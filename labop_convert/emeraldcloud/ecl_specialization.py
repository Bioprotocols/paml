import logging
from typing import Dict

import sbol3
import tyto
import xarray as xr

import labop
import uml
from labop.strings import Strings
from labop.utils.plate_coordinates import flatten_coordinates, get_sample_list
from labop_convert.behavior_specialization import (
    BehaviorSpecialization,
    ContO,
    validate_spec_query,
)

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


class ECLSpecialization(BehaviorSpecialization):
    MICROPLATE = "96 well microplate"
    MICROFUGE = "2 mL microfuge tube"
    STOCK_REAGENT_2mL = "2mL stock reagent container"
    STOCK_REAGENT_15mL = "15mL stock reagent container"
    STOCK_REAGENT_50mL = "50mL stock reagent container"
    STOCK_REAGENT = "stock reagent container"
    WASTE = "waste container"
    # Map terms in the Container ontology to OT2 API names
    LABWARE_MAP = {
        ContO[
            MICROPLATE
        ]: """Model[Container, Plate, "96-well Polystyrene Flat-Bottom Plate, Clear"]""",
        ContO[MICROFUGE]: """Model[Container, Vessel, "2mL Tube"]""",
        ContO[STOCK_REAGENT_2mL]: """Model[Container, Vessel, "2mL Tube"]""",
        ContO[STOCK_REAGENT_15mL]: """Model[Container, Vessel, "15mL Tube"]""",
        ContO[STOCK_REAGENT_50mL]: """Model[Container, Vessel, "50mL Tube"]""",
        ContO[STOCK_REAGENT]: """Model[Container, Vessel, "2mL Tube"]""",
        ContO[WASTE]: """Model[Container, Vessel, "2mL Tube"]""",
    }

    def __init__(
        self,
        filename,
        resolutions: Dict[sbol3.Identified, str] = None,
        create_stock_solutions=False,
    ) -> None:
        super().__init__()
        self.resolutions = resolutions if resolutions else {}
        self.var_to_entity = {}
        self.script = ""
        self.script_steps = []
        self.markdown = ""
        self.markdown_steps = []
        self.configuration = {}
        if len(filename.split(".")) == 1:
            filename += ".ecl"
        self.filename = filename
        self.sample_format = Strings.XARRAY
        self.create_stock_solutions = create_stock_solutions
        self.mapped_subprotocols = {
            "http://igem.org/engineering/Resuspend": self.resuspend,
            "http://igem.org/engineering/PrepareSolution": self.prepare_solution,
        }
        self.current_independent_subprotocol = None

        # Independent subprotocols are output as a separate protocol, whose outputs are referenced by the main protocol.
        self.independent_subprotocols = {
            "http://igem.org/engineering/PrepareSolution",
        }
        self.independent_subprotocol_steps = {}

        # Needed for using container ontology
        self.container_api_addl_conditions = "(cont:availableAt value <https://sift.net/container-ontology/strateos-catalog#Strateos>)"

    def _init_behavior_func_map(self) -> dict:
        """
        This function redirects processing of each primitive to the functions
        defined below.  Adding additional mappings here is most likely required.
        """
        return {
            "https://bioprotocols.org/labop/primitives/sample_arrays/EmptyContainer": self.define_container,
            "https://bioprotocols.org/labop/primitives/liquid_handling/Vortex": self.vortex,
            "https://bioprotocols.org/labop/primitives/liquid_handling/Provision": self.provision,
            "https://bioprotocols.org/labop/primitives/liquid_handling/Transfer": self.transfer_to,
            "https://bioprotocols.org/labop/primitives/liquid_handling/TransferByMap": self.transfer_by_map,
            "https://bioprotocols.org/labop/primitives/sample_arrays/PlateCoordinates": self.plate_coordinates,
            "https://bioprotocols.org/labop/primitives/spectrophotometry/MeasureAbsorbance": self.measure_absorbance,
            "https://bioprotocols.org/labop/primitives/sample_arrays/EmptyRack": self.define_rack,
            "https://bioprotocols.org/labop/primitives/sample_arrays/LoadContainerInRack": self.load_container_in_rack,
            "https://bioprotocols.org/labop/primitives/sample_arrays/LoadContainerOnInstrument": self.load_container_on_instrument,
            "https://bioprotocols.org/labop/primitives/sample_arrays/LoadRackOnInstrument": self.load_racks,
            "https://bioprotocols.org/labop/primitives/sample_arrays/ConfigureRobot": self.configure_robot,
            "https://bioprotocols.org/labop/primitives/pcr/PCR": self.pcr,
            "https://bioprotocols.org/labop/primitives/liquid_handling/SerialDilution": self.serial_dilution,
            "https://bioprotocols.org/labop/primitives/spectrophotometry/MeasureFluorescence": self.measure_fluorescence,
            "http://igem.org/engineering/PrepareReagents": self.prepare_reagents,
            "http://igem.org/engineering/PrepareSolution": {
                "start": self.prepare_solution,
                "end": self.finalize_prepare_solution,
            },
        }

    def handle_process_failure(self, record, exception):
        super().handle_process_failure(record, exception)
        self.script_steps.append(f"# Failure processing record: {record.identity}")

    def on_begin(self, ex: "ProtocolExecution"):
        protocol = self.execution.protocol.lookup()
        self.data = []

    def on_end(self, ex):
        self.script += self._compile_script()
        if self.filename:
            with open(self.filename, "w") as f:
                f.write(self.script)
            print(f"Successful execution. Script dumped to {self.filename}.")
        else:
            l.warn(
                "Writing output of specialization to self.data because no filename specified."
            )
            self.data = self.script

    def _compile_script(self):
        if self.create_stock_solutions:
            script = "\n".join(
                [
                    # f"""subprotocol_{k.replace(" ", "_")} = {v[0] + ",".join(v[1:-1])+v[-1]}"""
                    f"""subprotocol_{k.replace(" ", "_")} = {",".join(v)}"""
                    for k, v in self.independent_subprotocol_steps.items()
                    if len([l for l in v if l != ""]) > 0
                ]
            )
            script += "\n"
        else:
            script = "protocol = RoboticSamplePreparation[\n"
            self.script_steps = [f"  {step}" for step in self.script_steps]  # Indent
            script += ",\n".join(self.script_steps)
            script += "]"

        return script

    def define_container(
        self, record: "ActivityNodeExecution", ex: "ProtocolExecution"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        spec = parameter_value_map["specification"]
        samples = parameter_value_map["samples"]

        name = spec.name if spec.name else spec.display_id
        container_types = self.resolve_container_spec(spec)
        selected_container_type = self.check_lims_inventory(container_types)
        container = ecl_container(selected_container_type)

        # SampleArray fields are initialized in primitive_execution.py
        text = f"""LabelContainer[
    Label -> "{name}",
    Container -> {container}]"""

        # if self.current_independent_subprotocol:
        #     self.independent_subprotocol_steps[self.current_independent_subprotocol] += [text]
        # else:
        self.script_steps += [text]

    def vortex(
        self,
        record: "ActivityNodeExecution",
        execution: "ProtocolExecution",
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        duration = None
        if "duration" in parameter_value_map:
            duration_measure = ecl_measure(
                parameter_value_map["duration"], use_star=True
            )
        samples = parameter_value_map["samples"]
        spec = samples.get_container_type()
        if str(spec) in self.resolutions:
            sample = self.resolutions[str(spec)]
        else:
            sample = str(spec)

        text = f"""Mix[
      Sample -> {sample},
      MixType -> Vortex,
      Time -> ({duration_measure})
    ]"""

        if self.current_independent_subprotocol:
            self.independent_subprotocol_steps[
                self.current_independent_subprotocol
            ] += [text]
        else:
            self.script_steps += [text]

    def time_wait(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        value = parameter_value_map["amount"].value
        units = parameter_value_map["amount"].unit
        self.script_steps += [f"time.sleep(value)"]

    def provision(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        destination = parameter_value_map["destination"]
        resource = source = self.resolutions[parameter_value_map["resource"].identity]

        if type(destination) is labop.SampleMask:
            dest_container = destination.source.lookup().container_type.lookup()
            dest_wells = ecl_coordinates(destination)
        else:
            dest_container = destination.container_type.lookup()
            dest_wells = None

        amount = ecl_measure(parameter_value_map["amount"])
        text = ecl_transfer(
            source, f'"{dest_container}"', amount, dest_wells=dest_wells
        )

        # if self.current_independent_subprotocol:
        #     self.independent_subprotocol_steps[self.current_independent_subprotocol] += [text]
        # else:
        self.script_steps += [text]

    def transfer_to(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        source = parameter_value_map["source"]
        destination = parameter_value_map["destination"]
        amount = ecl_measure(parameter_value_map["amount"])

        if type(source) is labop.SampleMask:
            source_container = source.source.lookup().container_type.lookup()

            source_wells = ecl_coordinates(source)
        else:
            source_container = source.container_type.lookup()
            source_wells = None

        if type(destination) is labop.SampleMask:
            dest_container = destination.source.lookup().container_type.lookup()
            dest_wells = ecl_coordinates(destination)
        else:
            dest_container = destination.container_type.lookup()
            dest_wells = None

        # if source_container.identity in self.resolutions:
        #     resource = self.resolutions[source_container.identity]
        # else:
        resource = f'"{source_container.name}"'

        text = ecl_transfer(
            resource,
            f'"{dest_container}"',
            amount,
            src_wells=source_wells,
            dest_wells=dest_wells,
        )

        # if self.current_independent_subprotocol:
        #     self.independent_subprotocol_steps[self.current_independent_subprotocol] += [text]
        # else:
        self.script_steps += [text]

    def transfer_by_map(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        destination = parameter_value_map["destination"]
        source = parameter_value_map["source"]
        plan = parameter_value_map["plan"]
        temperature = parameter_value_map["temperature"]
        value = parameter_value_map["amount"].value

    def plate_coordinates(
        self, record: "ActivityNodeExecution", ex: "ProtocolExecution"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        source = parameter_value_map["source"]
        coords = parameter_value_map["coordinates"]
        samples = parameter_value_map["samples"]

    def measure_absorbance(
        self, record: "ActivityNodeExecution", ex: "ProtocolExecution"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        wavelength = ecl_measure(parameter_value_map["wavelength"])
        samples = parameter_value_map["samples"]

        if type(samples) is labop.SampleMask:
            samples = samples.source.lookup()
        container = samples.container_type.lookup()
        container_name = container.name if container.name else container.display_id

        text = f"""AbsorbanceIntensity[
      Sample -> "{container_name}",
      Wavelength -> {wavelength},
      PlateReaderMix -> True,
      PlateReaderMixRate -> 700 RPM,
      BlankAbsorbance -> False,
      Instrument -> Model[Instrument, PlateReader, "CLARIOstar"]
      ]"""
        self.script_steps += [text]

    def measure_fluorescence(
        self, record: "ActivityNodeExecution", ex: "ProtocolExecution"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        excitation = ecl_measure(parameter_value_map["excitationWavelength"])
        emission = ecl_measure(parameter_value_map["emissionWavelength"])
        bandpass = ecl_measure(parameter_value_map["emissionBandpassWidth"])
        samples = parameter_value_map["samples"]
        timepoints = (
            parameter_value_map["timepoints"]
            if "timepoints" in parameter_value_map
            else None
        )
        measurements = parameter_value_map["measurements"]

        if type(samples) is labop.SampleMask:
            samples = samples.source.lookup()
        container = samples.container_type.lookup()
        container_name = container.name if container.name else container.display_id

        text = f"""FluorescenceIntensity[
      Sample -> "{container_name}",
      ExcitationWavelength -> {excitation},
      EmissionWavelength -> {emission},
      Instrument -> Model[Instrument, PlateReader, "CLARIOstar"]
      ]"""
        self.script_steps += [text]

    def define_rack(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        spec = parameter_value_map["specification"]
        slots = parameter_value_map["slots"]

    def load_container_in_rack(
        self, record: "ActivityNodeExecution", ex: "ProtocolExecution"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        container: labop.ContainerSpec = parameter_value_map["container"]["value"]
        coords: str = (
            parameter_value_map["coordinates"]
            if "coordinates" in parameter_value_map
            else "A1"
        )
        slots: "SampleCollection" = parameter_value_map["slots"]
        samples: labop.SampleMask = parameter_value_map["samples"]

    def load_container_on_instrument(
        self, record: "ActivityNodeExecution", ex: "ProtocolExecution"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        container_spec: labop.ContainerSpec = parameter_value_map["specification"]
        slots: str = (
            parameter_value_map["slots"] if "slots" in parameter_value_map else "A1"
        )
        instrument: sbol3.Agent = parameter_value_map["instrument"]
        samples: labop.SampleArray = parameter_value_map["samples"]

    def load_racks(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        call = record.call.lookup()
        node = record.node.lookup()
        parameter_value_map = call.parameter_value_map()
        coords: str = (
            parameter_value_map["coordinates"]
            if "coordinates" in parameter_value_map
            else "1"
        )
        rack: labop.ContainerSpec = parameter_value_map["rack"]

    def configure_robot(self, record: "ActivityNodeExecution", ex: "ProtocolExecution"):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        instrument = parameter_value_map["instrument"]
        mount = parameter_value_map["mount"]

    def pcr(
        self,
        record: "ActivityNodeExecution",
        execution: "ProtocolExecution",
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        cycles = parameter_value_map["cycles"]
        annealing_temp = parameter_value_map["annealing_temp"]
        extension_temp = parameter_value_map["extension_temp"]
        denaturation_temp = parameter_value_map["denaturation_temp"]
        annealing_time = parameter_value_map["annealing_time"]
        extension_time = parameter_value_map["extension_time"]
        denaturation_time = parameter_value_map["denaturation_time"]

    def get_instrument_deck(self, instrument: sbol3.Agent) -> str:
        for deck, agent in self.configuration.items():
            if agent == instrument:
                return deck
        raise Exception(
            f"{instrument.display_id} is not currently configured for this robot"
        )

    def serial_dilution(
        self,
        record: "ActivityNodeExecution",
        execution: "ProtocolExecution",
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        source = parameter_value_map["samples"]
        destination = parameter_value_map["samples"]
        amount = ecl_measure(parameter_value_map["amount"])

        if isinstance(source, labop.SampleMask):
            source = source.source.lookup()
        source_container = source.container_type.lookup()
        source_container = source_container.name

        if isinstance(destination, labop.SampleMask):
            destination_coordinates = flatten_coordinates(
                destination.sample_coordinates(
                    sample_format=self.sample_format, as_list=True
                ),
                direction=Strings.COLUMN_DIRECTION,
            )
            destination = destination.source.lookup()

        # Get destination container type
        destination_container = destination.container_type.lookup()
        destination_container = destination_container.name

        sources = ",".join(map(str, destination_coordinates[:-1]))
        destinations = ",".join(map(str, destination_coordinates[1:]))
        source_wells = sources
        destination_wells = destinations

        self.script_steps += [
            ecl_transfer(
                f'"{source_container}"',
                f'"{destination_container}"',
                amount,
                src_wells=source_wells,
                dest_wells=destination_wells,
            )
        ]

    def resuspend(
        self,
        record: "ActivityNodeExecution",
        execution: "ProtocolExecution",
    ):
        pass

    #         call = record.call.lookup()
    #         parameter_value_map = call.parameter_value_map()

    #         source = parameter_value_map["source"]
    #         destination = parameter_value_map["destination"]
    #         amount = ecl_measure(parameter_value_map["amount"])

    #         if isinstance(source, labop.SampleMask):
    #             source = source.source.lookup()
    #         source_container = source.container_type.lookup()
    #         source_container = source_container.name

    #         if isinstance(destination, labop.SampleMask):
    #             destination_coordinates = flatten_coordinates(
    #                 destination.sample_coordinates(
    #                     sample_format=self.sample_format, as_list=True
    #                 ),
    #                 direction=Strings.COLUMN_DIRECTION,
    #             )
    #             destination = destination.source.lookup()

    #         # Get destination container type
    #         destination_container = destination.container_type.lookup()
    #         destination_container = destination_container.name

    #         self.script_steps += [
    #             f"""
    #    Resuspend[
    #      Sample -> "{destination_container}",
    #      Diluent -> "{source_container}",
    #      Volume -> {amount},
    #      DispenseNumberOfMixes -> 3,
    #      DispenseMix -> True
    #      ] """
    #         ]

    def prepare_solution(self, record: "ActivityNodeExecution", execution: "Protocol"):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        spec = parameter_value_map["specification"]
        self.current_independent_subprotocol = spec.name

        buffer_container = parameter_value_map["buffer_container"]
        buffer = parameter_value_map["buffer"]
        if (
            buffer_container.identity in self.resolutions
            and not self.create_stock_solutions
        ):
            resource = self.resolutions[buffer_container.identity]
        elif buffer.identity in self.resolutions and self.create_stock_solutions:
            resource = self.resolutions[buffer.identity]
        else:
            resource = f'"{buffer_container.name}"'
        buffer_vol = ecl_measure(parameter_value_map["buffer_volume"], use_star=True)

        reagent = parameter_value_map["reagent"]
        if reagent.identity in self.resolutions:
            reagent_resource = self.resolutions[reagent.identity]
        else:
            reagent_resource = f'"{reagent.name}"'
        reagent_mass = ecl_measure(parameter_value_map["reagent_mass"], use_star=True)

        if self.create_stock_solutions:
            # Generate a stock solution recipe
            components = f"""{{{buffer_vol}, {resource}}}, {{{reagent_mass}, {reagent_resource}}}"""
            self.independent_subprotocol_steps[spec.name] = [
                f"""ExperimentStockSolution[{{{components}}}, MixTime-> 30 Second]"""
            ]
        else:
            self.independent_subprotocol_steps[spec.name] = [""]
            container_types = self.resolve_container_spec(spec)
            selected_container_type = self.check_lims_inventory(container_types)
            container = ecl_container(selected_container_type)

            self.script_steps += [
                f"""LabelContainer[
    Label -> "{spec.name}",
    Container -> {container}]
        """,
                ecl_transfer(reagent_resource, f'"{spec.name}"', buffer_vol),
            ]

    def finalize_prepare_solution(
        self, record: "ActivityNodeExecution", execution: "Protocol"
    ):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        self.current_independent_subprotocol = None
        spec = parameter_value_map["specification"]
        # self.independent_subprotocol_steps[spec.name] += ["}]"]

    def prepare_reagents(
        self,
        record: "ActivityNodeExecution",
        execution: "ProtocolExecution",
    ):
        pass

    #     self.stock_solutions += """

    # "1x PBS from 10X stock"
    # "Nuclease-free Water"
    # "1x PBS, 10uM Fluorescein"

    # ExperimentStockSolution[
    #     Model[Sample, StockSolution, ""Silica beads 2.96mg/mL 950nm""],
    #     Volume -> 2 Milliliter,
    #     MixType -> Pipette,
    #     MixTime -> Null,
    #     ContainerOut -> Model[Container, Vessel, "2mL brown tube"]
    # ]
    #     """


def ecl_container(container_type: tyto.URI):
    if container_type in ECLSpecialization.LABWARE_MAP:
        container = ECLSpecialization.LABWARE_MAP[container_type]
        return container
        # return f'Model[Container, Vessel, "{container}"]'
    if container_type in ContO[ECLSpecialization.MICROPLATE].get_instances():
        container = ECLSpecialization.LABWARE_MAP[ContO[ECLSpecialization.MICROPLATE]]
        return container
        # return f'Model[Container, Plate, "{container}"]'
    if container_type in ContO[ECLSpecialization.MICROFUGE].get_instances():
        container = ECLSpecialization.LABWARE_MAP[ContO[ECLSpecialization.MICROFUGE]]
        return container
        # return f'Model[Container, Vessel, "{container}"]'
    if container_type in ContO[ECLSpecialization.STOCK_REAGENT_15mL].get_instances():
        container = ECLSpecialization.LABWARE_MAP[
            ContO[ECLSpecialization.STOCK_REAGENT_15mL]
        ]
    if container_type in ContO[ECLSpecialization.STOCK_REAGENT_50mL].get_instances():
        container = ECLSpecialization.LABWARE_MAP[
            ContO[ECLSpecialization.STOCK_REAGENT_50mL]
        ]
    if container_type in ContO[ECLSpecialization.STOCK_REAGENT_2mL].get_instances():
        container = ECLSpecialization.LABWARE_MAP[
            ContO[ECLSpecialization.STOCK_REAGENT_2mL]
        ]

        # return f'Model[Container, Vessel, "{container}"]'
    raise Exception(
        f"Load failed. Container {container_type} is not supported labware."
    )


def ecl_measure(measure: sbol3.Measure, use_star=False):
    text = str(measure.value) + (" *" if use_star else "")
    if measure.unit == tyto.OM.microliter:
        return text + " Microliter"
    elif measure.unit == tyto.OM.nanometer:
        return text + " Nanometer"
    elif measure.unit == tyto.OM.milliliter:
        return text + " Milliliter"
    elif measure.unit == tyto.OM.microgram:
        return text + " Microgram"
    elif measure.unit == tyto.OM.milligram:
        return text + " Milligram"
    elif measure.unit == tyto.OM.second:
        return text + " Second"

    raise ValueError(tyto.OM.get_term_by_uri(measure.unit) + " is not a supported unit")


def ecl_coordinates(samples: "SampleCollection", sample_format=Strings.XARRAY):
    if type(samples) is labop.SampleMask:
        coordinates = flatten_coordinates(
            samples.sample_coordinates(sample_format=sample_format, as_list=True),
            direction=Strings.COLUMN_DIRECTION,
        )

        # Get destination container type
        samples = samples.source.lookup()
        container = samples.container_type.lookup()
        container_name = container.name if container.name else container.display_id
        locations = ",".join(map(str, coordinates))
        return locations
        # return f"""{{#, "{container_name}"}} & /@  Flatten[Transpose[AllWells[]]][[{ {locations} }]]"""

    raise TypeError()


def ecl_transfer(
    source: str,
    destination: str,
    amount: str,
    src_wells: str = None,
    dest_wells: str = None,
    options="SlurryTransfer -> True, DispenseMix -> True",
):
    if src_wells:
        src_id = "#1"
        dest_id = "#2"
    else:
        dest_id = "#1"

    if dest_wells:
        dest_well_list = f"Flatten[Transpose[AllWells[]]][[{{{dest_wells}}}]]"
        dest_well_attr = f"\n        DestinationWell -> {dest_id},"
    else:
        dest_well_list = None
        dest_well_attr = f""

    if src_wells:
        src_well_list = f"Flatten[Transpose[AllWells[]]][[{{{src_wells}}}]]"
        src_well_attr = f"\n        SourceWell -> {src_id},"
    else:
        src_well_list = None
        src_well_attr = f""

    if src_wells or dest_wells:
        prefix = "Sequence@@MapThread["
        well_mapping = ",".join(
            ([src_well_list] if src_well_list else [])
            + ([dest_well_list] if dest_well_list else [])
        )
        suffix = f" &,{{{well_mapping}}}]"
    else:
        prefix = ""
        suffix = ""

    return f"""
  {prefix}Transfer[
        Source -> {source},{src_well_attr}
        Destination -> {destination},{dest_well_attr}
        Amount -> {amount},
        {options}]{suffix}"""
