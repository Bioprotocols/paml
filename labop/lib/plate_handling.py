import sbol3

import labop

#############################################
# Set up the document
doc = sbol3.Document()
LIBRARY_NAME = "plate_handling"
sbol3.set_namespace("https://bioprotocols.org/labop/primitives/" + LIBRARY_NAME)


#############################################
# Create the primitives
print("Making primitives for " + LIBRARY_NAME)

# Note: plate handling primitives operate on whole arrays only, not just fragments
p = labop.Primitive("Cover")
p.description = "Cover a set of samples to keep materials from entering or exiting"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input("type", "http://www.w3.org/2001/XMLSchema#anyURI")
doc.add(p)

p = labop.Primitive("Seal")
p.description = "Seal a collection of samples fixing the seal using a user-selected method, in order to guarantee isolation from the external environment"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input(
    "specification", "http://bioprotocols.org/labop#ContainerSpec"
)  # e.g., breathable vs. non-breathable
doc.add(p)


p = labop.Primitive("Filter")
p.description = "Activate vacuum pump to perform filtering in a plate"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
doc.add(p)


p = labop.Primitive("EvaporativeSeal")
p.description = "Seal a collection of samples using a user-selected method in order to prevent evaporation"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input(
    "specification", "http://bioprotocols.org/labop#ContainerSpec"
)  # e.g., breathable vs. non-breathable
doc.add(p)

p = labop.Primitive("AdhesiveSeal")
p.description = "Seal a collection of samples using adhesive to fix the seal, in order to guarantee isolation from the external environment"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input(
    "type", "http://www.w3.org/2001/XMLSchema#anyURI"
)  # e.g., breathable vs. non-breathable
doc.add(p)

p = labop.Primitive("ThermalSeal")
p.description = "Seal a collection of samples using heat to fix the seal, in order to guarantee isolation from the external environment"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input(
    "type", "http://www.w3.org/2001/XMLSchema#anyURI"
)  # e.g., breathable vs. non-breathable
p.add_input("temperature", sbol3.OM_MEASURE)
p.add_input(
    "duration", sbol3.OM_MEASURE
)  # length of time to apply the sealing temperature in order to get the seal in place
doc.add(p)

p = labop.Primitive("Uncover")
p.description = "Uncover a collection of samples to allow materials to enter or exit"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
doc.add(p)

p = labop.Primitive("Unseal")
p.description = "Unseal a sealed collection of samples to break their isolation from the external environment"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
doc.add(p)

p = labop.Primitive("Incubate")
p.description = (
    "Incubate a set of samples under specified conditions for a fixed period of time"
)
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input("duration", sbol3.OM_MEASURE)  # time
p.add_input("temperature", sbol3.OM_MEASURE)  # temperature
p.add_input(
    "shakingFrequency", sbol3.OM_MEASURE, True
)  # Hertz or RPM?; in either case, defaults to zero
doc.add(p)

p = labop.Primitive("Hold")
p.description = "Incubate, store, or hold a set of samples indefinitely at the specified temperature"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray", unbounded=True)
p.add_input("temperature", sbol3.OM_MEASURE)  # temperature
doc.add(p)

p = labop.Primitive("HoldOnIce")
p.description = "Incubate, store, or hold a set of samples indefinitely on ice"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray", unbounded=True)
doc.add(p)

p = labop.Primitive("Spin")
p.description = (
    "Centrifuge a set of samples at a given acceleration for a given period of time"
)
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
p.add_input("duration", sbol3.OM_MEASURE)  # time
p.add_input("acceleration", sbol3.OM_MEASURE)  # acceleration
doc.add(p)

p = labop.Primitive("QuickSpin")
p.description = "Perform a brief centrifugation on a set of samples to pull down stray droplets or condensate into the bottom of the container"
p.add_input("location", "http://bioprotocols.org/labop#SampleArray")
doc.add(p)

print("Library construction complete")
print("Validating library")
for e in doc.validate().errors:
    print(e)
for w in doc.validate().warnings:
    print(w)

filename = LIBRARY_NAME + ".ttl"
doc.write(filename, "turtle")
print("Library written as " + filename)
