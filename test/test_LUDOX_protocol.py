import sbol3
import paml
import tyto
import unittest


class TestProtocolEndToEnd(unittest.TestCase):
    def test_create_protocol(self):
        #############################################
        # set up the document
        doc = sbol3.Document()
        sbol3.set_namespace('https://bbn.com/scratch/')

        #############################################
        # Import the primitive libraries
        paml.import_library(doc, 'liquid_handling')
        paml.import_library(doc, 'plate_handling')
        paml.import_library(doc, 'spectrophotometry')

        #############################################
        # Create the protocol
        protocol = paml.Protocol('iGEM_LUDOX_OD_calibration_2018')
        protocol.name = "iGEM 2018 LUDOX OD calibration protocol"
        protocol.description = '''
        With this protocol you will use LUDOX CL-X (a 45% colloidal silica suspension) as a single point reference to
        obtain a conversion factor to transform absorbance (OD600) data from your plate reader into a comparable
        OD600 measurement as would be obtained in a spectrophotometer. This conversion is necessary because plate
        reader measurements of absorbance are volume dependent; the depth of the fluid in the well defines the path
        length of the light passing through the sample, which can vary slightly from well to well. In a standard
        spectrophotometer, the path length is fixed and is defined by the width of the cuvette, which is constant.
        Therefore this conversion calculation can transform OD600 measurements from a plate reader (i.e. absorbance
        at 600 nm, the basic output of most instruments) into comparable OD600 measurements. The LUDOX solution
        is only weakly scattering and so will give a low absorbance value.
        '''
        doc.add(protocol)

        # create the materials to be provisioned
        plate = paml.Container(name='Microplate', type=tyto.NCIT.get_uri_by_term('Microplate'))
        protocol.hasLocation.append(plate)

        ddh2o = sbol3.Component('ddH2O', 'https://identifiers.org/pubchem.substance:24901740')
        ddh2o.name = 'Water, sterile-filtered, BioReagent, suitable for cell culture'  # TODO get via tyto
        doc.add(ddh2o)

        ludox = sbol3.Component('LUDOX', 'https://identifiers.org/pubchem.substance:24866361')
        ludox.name = 'LUDOX(R) CL-X colloidal silica, 45 wt. % suspension in H2O'
        doc.add(ludox)

        protocol.material += {ddh2o, ludox}

        # actual steps of the protocol
        location = paml.ContainerCoordinates()
        protocol.hasLocation.append(location)
        location.inContainer = plate
        location.coordinates = 'A1:D1'
        provision_ludox = paml.make_PrimitiveExecutable(doc.find('Provision'), resource=ludox, destination=location,
                                                        amount=sbol3.Measure(100, tyto.OM.microliter))
        protocol.hasActivity.append(provision_ludox)
        protocol.add_flow(protocol.initial(), provision_ludox)

        location = paml.ContainerCoordinates()
        protocol.hasLocation.append(location)
        location.inContainer = plate
        location.coordinates = 'A2:D2'
        provision_ddh2o = paml.make_PrimitiveExecutable(doc.find('Provision'), resource=ddh2o, destination=location,
                                                        amount=sbol3.Measure(100, tyto.OM.microliter))
        protocol.hasActivity.append(provision_ddh2o)
        protocol.add_flow(protocol.initial(), provision_ddh2o)
        # For consistent serialization for this test, also order the two provisions
        protocol.add_flow(provision_ludox, provision_ddh2o)

        all_provisioned = paml.Join()
        protocol.hasActivity.append(all_provisioned)
        protocol.add_flow(provision_ludox.output_pin('samples', doc), all_provisioned)
        protocol.add_flow(provision_ddh2o.output_pin('samples', doc), all_provisioned)

        execute_measurement = paml.make_PrimitiveExecutable(doc.find('MeasureAbsorbance'),
                                                            wavelength=sbol3.Measure(600, tyto.OM.nanometer))
        protocol.hasActivity.append(execute_measurement)
        protocol.add_flow(all_provisioned, execute_measurement.input_pin('samples', doc))

        result = paml.Value()
        protocol.hasActivity.append(result)
        protocol.add_flow(execute_measurement.output_pin('measurements', doc), result)

        protocol.add_flow(result, protocol.final())

        protocol.output += {result}

        ########################################
        # Validate and write the document
        v = doc.validate()
        assert not v.errors and v.warnings

        doc.write('igem_ludox_draft.json', 'json-ld')
        doc.write('igem_ludox_draft.ttl', 'turtle')


if __name__ == '__main__':
    unittest.main()
