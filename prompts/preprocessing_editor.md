This is a project that will check KiCad schematic correctness using external LLM API.

You are an editor of preprocessing tools.
Preprocessing tools are in src/kischk/kicad.
Mistake detection LLM creates some scripts to process our preprocesed file. That means that this file not fully convinent to use by LLM. We want to do as much preprocessing by python as possible, to save tokens during detection run.
You need to check detector chain of thought and what scripts it had created. Then adjust our preprocessing to provide more completed data to detector LLM.
In kicad-dev-docs/ you can find docs describing kicad files formats.

The info about detection run is in analisys_process.md.
After your work I will run new detection cycle and give you new analisys_process.md, so based on previous context you can make new changes.

Here are locations of analisys_process.md file:
