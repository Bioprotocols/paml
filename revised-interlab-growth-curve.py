"""
http://2018.igem.org/wiki/images/0/09/2018_InterLab_Plate_Reader_Protocol.pdf
"""
import json
from urllib.parse import quote

import sbol3
from tyto import OM

import labop
import uml
from labop.execution.execution_engine import ExecutionEngine
from labop_convert import MarkdownSpecialization

if "unittest" in sys.modules:
    REGENERATE_ARTIFACTS = False
else:
    REGENERATE_ARTIFACTS = True

filename = "".join(__file__.split(".py")[0].split("/")[-1:])

doc = sbol3.Document()
sbol3.set_namespace("http://igem.org/engineering/")

#############################################
# Import the primitive libraries
print("Importing libraries")
labop.import_library("liquid_handling")
print("... Imported liquid handling")
labop.import_library("plate_handling")
# print('... Imported plate handling')
labop.import_library("spectrophotometry")
print("... Imported spectrophotometry")
labop.import_library("sample_arrays")
print("... Imported sample arrays")
labop.import_library("culturing")
#############################################


# create the materials to be provisioned
dh5alpha = sbol3.Component(
    "dh5alpha", "https://identifiers.org/pubchem.substance:24901740"
)
dh5alpha.name = "_E. coli_ DH5 alpha"
doc.add(dh5alpha)

lb_cam = sbol3.Component("lb_cam", "https://identifiers.org/pubchem.substance:24901740")
lb_cam.name = "LB Broth+chloramphenicol"
doc.add(lb_cam)

chloramphenicol = sbol3.Component(
    "chloramphenicol", "https://identifiers.org/pubchem.substance:24901740"
)
chloramphenicol.name = "chloramphenicol"
doc.add(chloramphenicol)


neg_control_plasmid = sbol3.Component("neg_control_plasmid", sbol3.SBO_DNA)
neg_control_plasmid.name = "Negative control"
neg_control_plasmid.description = "BBa_R0040 Kit Plate 1 Well 12M"

pos_control_plasmid = sbol3.Component("pos_control_plasmid", sbol3.SBO_DNA)
pos_control_plasmid.name = "Positive control"
pos_control_plasmid.description = "BBa_I20270 Kit Plate 1 Well 1A"

test_device1 = sbol3.Component("test_device1", sbol3.SBO_DNA)
test_device1.name = "Test Device 1"
test_device1.description = "BBa_J364000 Kit Plate 1 Well 1C"

test_device2 = sbol3.Component("test_device2", sbol3.SBO_DNA)
test_device2.name = "Test Device 2"
test_device2.description = "BBa_J364001 Kit Plate 1 Well 1E"

test_device3 = sbol3.Component("test_device3", sbol3.SBO_DNA)
test_device3.name = "Test Device 3"
test_device3.description = "BBa_J364002 Kit Plate 1 Well 1G"

test_device4 = sbol3.Component("test_device4", sbol3.SBO_DNA)
test_device4.name = "Test Device 4"
test_device4.description = "BBa_J364007 Kit Plate 1 Well 1I"

test_device5 = sbol3.Component("test_device5", sbol3.SBO_DNA)
test_device5.name = "Test Device 5"
test_device5.description = "BBa_J364008 Kit Plate 1 Well 1K"

test_device6 = sbol3.Component("test_device6", sbol3.SBO_DNA)
test_device6.name = "Test Device 6"
test_device6.description = "BBa_J364009 Kit Plate 1 Well 1M"

doc.add(neg_control_plasmid)
doc.add(pos_control_plasmid)
doc.add(test_device1)
doc.add(test_device2)
doc.add(test_device3)
doc.add(test_device4)
doc.add(test_device5)
doc.add(test_device6)


activity = labop.Protocol("interlab")
activity.name = "Cell measurement protocol"
activity.version = sbol3.TextProperty(
    activity, "http://igem.org/interlab_working_group#Version", 0, 1, [], "1.0b"
)
activity.description = """This year we plan to go towards automation, where a 96-well plate instead of a tube is used for culturing. Prior to the full establishment of this protocol, we need to evaluate how the performance is worldwide with this as well as with parallel experiment in the test tube, which has been used as standard culturing protocol.

At the end of the experiment, you would have two plates to be measured (five for challenging version). You will measure both fluorescence and absorbance in each plate.

Prior to performing the cell measurements you should perform all three of the calibration measurements. Please do not proceed unless you have completed the three calibration protocols. Completion of the calibrations will ensure that you understand the measurement process and that you can take the cell measurements under the same conditions. For the sake of consistency and reproducibility, we are requiring all teams to use E. coli K-12 DH5-alpha. If you do not have access to this strain, you can request streaks of the transformed devices from another team near you, and this can count as a collaboration as long as it is appropriately documented on both teams' wikis. If you are absolutely unable to obtain the DH5-alpha strain, you may still participate in the InterLab study by contacting the Measurement Committee (measurement at igem dot org) to discuss your situation.

For all of these cell measurements, you must use the same plates and volumes that you used in your calibration protocol. You must also use the same settings (e.g., filters or excitation and emission wavelengths) that you used in your calibration measurements. If you do not use the same plates, volumes, and settings, the measurements will not be valid."""

doc.add(activity)
activity = doc.find(activity.identity)

plasmids = [
    neg_control_plasmid,
    pos_control_plasmid,
    test_device1,
    test_device2,
    test_device3,
    test_device4,
    test_device5,
    test_device6,
]

# Day 1: Transformation
transformation = activity.primitive_step(
    f"Transform", host=dh5alpha, dna=plasmids, selection_medium=lb_cam
)

# Day 2: Pick colonies and culture overnight
culture_container_day1 = activity.primitive_step(
    "ContainerSet",
    quantity=2 * len(plasmids),
    specification=labop.ContainerSpec(
        name=f"culture (day 1)",
        queryString="cont:CultureTube",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)

overnight_culture = activity.primitive_step(
    "Culture",
    inoculum=transformation.output_pin("transformants"),
    replicates=2,
    growth_medium=lb_cam,
    volume=sbol3.Measure(5, OM.millilitre),  # Actually 5-10 ml in the written protocol
    duration=sbol3.Measure(16, OM.hour),  # Actually 16-18 hours
    orbital_shake_speed=sbol3.Measure(220, None),  # No unit for RPM or inverse minutes
    temperature=sbol3.Measure(37, OM.degree_Celsius),
    container=culture_container_day1.output_pin("samples"),
)

# Day 3 culture
culture_container_day2 = activity.primitive_step(
    "ContainerSet",
    quantity=2 * len(plasmids),
    specification=labop.ContainerSpec(
        name=f"culture (day 2)",
        queryString="cont:CultureTube",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)


back_dilution = activity.primitive_step(
    "Dilute",
    source=culture_container_day1.output_pin("samples"),
    destination=culture_container_day2.output_pin("samples"),
    replicates=2,
    diluent=lb_cam,
    amount=sbol3.Measure(5.0, OM.millilitre),
    dilution_factor=uml.LiteralInteger(value=10),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)

# Transfer cultures to a microplate baseline measurement and outgrowth
timepoint_0hrs = activity.primitive_step(
    "ContainerSet",
    quantity=2 * len(plasmids),
    specification=labop.ContainerSpec(
        name="cultures (0 hr timepoint)",
        queryString="cont:MicrofugeTube",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)

hold = activity.primitive_step(
    "Hold",
    location=timepoint_0hrs.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)
hold.description = "This will prevent cell growth while transferring samples."

transfer = activity.primitive_step(
    "Transfer",
    source=culture_container_day2.output_pin("samples"),
    destination=timepoint_0hrs.output_pin("samples"),
    amount=sbol3.Measure(1, OM.milliliter),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)

baseline_absorbance = activity.primitive_step(
    "MeasureAbsorbance",
    samples=timepoint_0hrs.output_pin("samples"),
    wavelength=sbol3.Measure(600, OM.nanometer),
)
baseline_absorbance.name = "baseline absorbance of culture (day 2)"


conical_tube = activity.primitive_step(
    "ContainerSet",
    quantity=2 * len(plasmids),
    specification=labop.ContainerSpec(
        name=f"back-diluted culture",
        queryString="cont:50mlConicalTube",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)
conical_tube.description = (
    "The conical tube should be opaque, amber-colored, or covered with foil."
)

dilution = activity.primitive_step(
    "DiluteToTargetOD",
    source=culture_container_day2.output_pin("samples"),
    destination=conical_tube.output_pin("samples"),
    diluent=lb_cam,
    amount=sbol3.Measure(12, OM.millilitre),
    target_od=sbol3.Measure(0.02, None),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)  # Dilute to a target OD of 0.2, opaque container
dilution.description = " Use the provided Excel sheet to calculate this dilution. Reliability of the dilution upon Abs600 measurement: should stay between 0.1-0.9"

embedded_image = activity.primitive_step(
    "EmbeddedImage",
    image="/Users/bbartley/Dev/git/sd2/labop/fig1_cell_calibration.png",
)


temporary = activity.primitive_step(
    "ContainerSet",
    quantity=2 * len(plasmids),
    specification=labop.ContainerSpec(
        name="back-diluted culture aliquots",
        queryString="cont:MicrofugeTube",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)

hold = activity.primitive_step(
    "Hold",
    location=temporary.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)
hold.description = "This will prevent cell growth while transferring samples."

transfer = activity.primitive_step(
    "Transfer",
    source=conical_tube.output_pin("samples"),
    destination=temporary.output_pin("samples"),
    amount=sbol3.Measure(1, OM.milliliter),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)

plate1 = activity.primitive_step(
    "EmptyContainer",
    specification=labop.ContainerSpec(
        name="plate 1",
        queryString="cont:Plate96Well",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)


hold = activity.primitive_step(
    "Hold",
    location=plate1.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)


plan = labop.SampleData(
    values=quote(
        json.dumps(
            {
                "1": "A2:D2",
                "2": "E2:H2",
                "3": "A3:D3",
                "4": "E3:H3",
                "5": "A4:D4",
                "6": "E4:H4",
                "7": "A5:D5",
                "8": "E5:H5",
                "9": "A7:D7",
                "10": "E7:H7",
                "11": "A8:D8",
                "12": "E8:H8",
                "13": "A9:D9",
                "14": "E9:H9",
                "15": "A10:D10",
                "16": "E10:H10",
            }
        )
    )
)


transfer = activity.primitive_step(
    "TransferByMap",
    source=timepoint_0hrs.output_pin("samples"),
    destination=plate1.output_pin("samples"),
    amount=sbol3.Measure(100, OM.microliter),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
    plan=plan,
)
transfer.description = "See also the plate layout below."

plate_blanks = activity.primitive_step(
    "Transfer",
    source=[lb_cam],
    destination=plate1.output_pin("samples"),
    coordinates="A1:H1, A10:H10, A12:H12",
    temperature=sbol3.Measure(4, OM.degree_Celsius),
    amount=sbol3.Measure(100, OM.microliter),
)
plate_blanks.description = "These samples are blanks."

embedded_image = activity.primitive_step(
    "EmbeddedImage",
    image="/Users/bbartley/Dev/git/sd2/labop/fig2_cell_calibration.png",
)

# Cover plate
seal = activity.primitive_step(
    "EvaporativeSeal", location=plate1.output_pin("samples"), type="foo"
)


# Possibly display map here
absorbance_plate1 = activity.primitive_step(
    "MeasureAbsorbance",
    samples=plate1.output_pin("samples"),
    wavelength=sbol3.Measure(600, OM.nanometer),
)
absorbance_plate1.name = "0 hr absorbance timepoint"
fluorescence_plate1 = activity.primitive_step(
    "MeasureFluorescence",
    samples=plate1.output_pin("samples"),
    excitationWavelength=sbol3.Measure(488, OM.nanometer),
    emissionWavelength=sbol3.Measure(530, OM.nanometer),
    emissionBandpassWidth=sbol3.Measure(30, OM.nanometer),
)
fluorescence_plate1.name = "0 hr fluorescence timepoint"


# Begin outgrowth
incubate = activity.primitive_step(
    "Incubate",
    location=conical_tube.output_pin("samples"),
    duration=sbol3.Measure(6, OM.hour),
    temperature=sbol3.Measure(37, OM.degree_Celsius),
    shakingFrequency=sbol3.Measure(220, None),
)

incubate = activity.primitive_step(
    "Incubate",
    location=plate1.output_pin("samples"),
    duration=sbol3.Measure(6, OM.hour),
    temperature=sbol3.Measure(37, OM.degree_Celsius),
    shakingFrequency=sbol3.Measure(220, None),
)

# Hold on ice to inhibit cell growth
hold = activity.primitive_step(
    "Hold",
    location=timepoint_0hrs.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)
hold.description = (
    "This will inhibit cell growth during the subsequent pipetting steps."
)

hold = activity.primitive_step(
    "Hold",
    location=plate1.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)
hold.description = (
    "This will inhibit cell growth during the subsequent pipetting steps."
)


# Take a 6hr timepoint measurement
timepoint_6hrs = activity.primitive_step(
    "ContainerSet",
    quantity=len(plasmids) * 2,
    specification=labop.ContainerSpec(
        name=f"6hr timepoint",
        queryString="cont:MicrofugeTube",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)

plate2 = activity.primitive_step(
    "EmptyContainer",
    specification=labop.ContainerSpec(
        name="plate 2",
        queryString="cont:Plate96Well",
        prefixMap={"cont": "https://sift.net/container-ontology/container-ontology#"},
    ),
)

# Hold on ice
hold = activity.primitive_step(
    "Hold",
    location=timepoint_6hrs.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)
hold.description = "This will prevent cell growth while transferring samples."

hold = activity.primitive_step(
    "Hold",
    location=plate2.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
)


transfer = activity.primitive_step(
    "Transfer",
    source=conical_tube.output_pin("samples"),
    destination=timepoint_6hrs.output_pin("samples"),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
    amount=sbol3.Measure(1, OM.milliliter),
)


plan = labop.SampleData(
    values=quote(
        json.dumps(
            {
                "1": "A2:D2",
                "2": "E2:H2",
                "3": "A3:D3",
                "4": "E3:H3",
                "5": "A4:D4",
                "6": "E4:H4",
                "7": "A5:D5",
                "8": "E5:H5",
                "9": "A7:D7",
                "10": "E7:H7",
                "11": "A8:D8",
                "12": "E8:H8",
                "13": "A9:D9",
                "14": "E9:H9",
                "15": "A10:D10",
                "16": "E10:H10",
            }
        )
    )
)

transfer = activity.primitive_step(
    "TransferByMap",
    source=timepoint_6hrs.output_pin("samples"),
    destination=plate2.output_pin("samples"),
    amount=sbol3.Measure(100, OM.microliter),
    temperature=sbol3.Measure(4, OM.degree_Celsius),
    plan=plan,
)
transfer.description = "See the plate layout."

# Plate the blanks
plate_blanks = activity.primitive_step(
    "Transfer",
    source=[lb_cam],
    destination=plate2.output_pin("samples"),
    coordinates="A1:H1, A10:H10, A12:H12",
    temperature=sbol3.Measure(4, OM.degree_Celsius),
    amount=sbol3.Measure(100, OM.microliter),
)
plate_blanks.description = "These are the blanks."

# Cover plate
seal = activity.primitive_step(
    "EvaporativeSeal", location=plate1.output_pin("samples"), type="foo"
)


# quick_spin = protocol.primitive_step('QuickSpin',
#                                     location=plate1.output_pin('samples'))
# quick_spin.description = 'This will prevent cross-contamination when removing the seal.'
#
# remove_seal = protocol.primitive_step('Unseal',
#                                      location=plate1.output_pin('samples'))

endpoint_absorbance_plate1 = activity.primitive_step(
    "MeasureAbsorbance",
    samples=plate1.output_pin("samples"),
    wavelength=sbol3.Measure(600, OM.nanometer),
)
endpoint_absorbance_plate1.name = "6 hr absorbance timepoint"

endpoint_fluorescence_plate1 = activity.primitive_step(
    "MeasureFluorescence",
    samples=plate1.output_pin("samples"),
    excitationWavelength=sbol3.Measure(485, OM.nanometer),
    emissionWavelength=sbol3.Measure(530, OM.nanometer),
    emissionBandpassWidth=sbol3.Measure(30, OM.nanometer),
)
endpoint_fluorescence_plate1.name = "6 hr fluorescence timepoint"

endpoint_absorbance_plate2 = activity.primitive_step(
    "MeasureAbsorbance",
    samples=plate2.output_pin("samples"),
    wavelength=sbol3.Measure(600, OM.nanometer),
)
endpoint_absorbance_plate2.name = "6 hr absorbance timepoint"

endpoint_fluorescence_plate2 = activity.primitive_step(
    "MeasureFluorescence",
    samples=plate2.output_pin("samples"),
    excitationWavelength=sbol3.Measure(485, OM.nanometer),
    emissionWavelength=sbol3.Measure(530, OM.nanometer),
    emissionBandpassWidth=sbol3.Measure(30, OM.nanometer),
)
endpoint_fluorescence_plate2.name = "6 hr fluorescence timepoint"

activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=baseline_absorbance.output_pin("measurements"),
)
activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=absorbance_plate1.output_pin("measurements"),
)
activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=fluorescence_plate1.output_pin("measurements"),
)

activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=endpoint_absorbance_plate1.output_pin("measurements"),
)
activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=endpoint_fluorescence_plate1.output_pin("measurements"),
)

activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=endpoint_absorbance_plate2.output_pin("measurements"),
)
activity.designate_output(
    "measurements",
    "http://bioprotocols.org/labop#SampleData",
    source=endpoint_fluorescence_plate2.output_pin("measurements"),
)


agent = sbol3.Agent("test_agent")
ee = ExecutionEngine(specializations=[MarkdownSpecialization("test_LUDOX_markdown.md")])
execution = ee.execute(activity, agent, id="test_execution", parameter_values=[])
print(ee.specializations[0].markdown)
ee.specializations[0].markdown = ee.specializations[0].markdown.replace(
    "`_E. coli_", "_`E. coli`_ `"
)

filename = "".join(__file__.split(".py")[0].split("/")[-1:])

if REGENERATE_ARTIFACTS:
    with open(filename + ".md", "w", encoding="utf-8") as f:
        f.write(ee.specializations[0].markdown)
