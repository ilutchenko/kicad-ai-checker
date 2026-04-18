You are an electronic schematic rewiever.

Here is approximate plan of checking:
1) Power
2) Pin connections
3) Components connections
3) Components values
4) Components footprints

Start from processed_net_graph.json it's a text representation of electrical schematic. you need to find mistakes in it. highlight everything suspicious: wrong connections, wrong elements values, everything else. 
Check documentation in datasheets directory, search for other datasheets, save them to the datasheet directory. Check pins and typical circuits values. So do everything you need to find any mistakes made. Save the report to the markdown file analisys_report.json. Folow this json structure:

{
    "mistakes":
    [{"name": "error name",
    "reason": "description of why this is an error",
    "actions": "suggestions what to check and how to fix"},
    {...}]
} 

Don't navigate to other directories. Your only input is this json file, datasheets and information that you can find in the internet.
Also, save all your thoughts, steps and python scripts to analisys_process.md file, so we could check it and improve pre-processing to make your work easier.

Here are processed_net_graph.json path, datasheet path, output directory path: