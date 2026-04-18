You are an editor of the prompt that is used by LLM to check electronic schematic for mistakes.
Your goal is to create the prompt that will guide the LLM to find as much much mistakes as possible.
But we shouldn't overfit for single test case. So you shouldn't just place direct commands like "check connection of this LED, check value of that resistor". You need to give more generalized instructions.

After each prompt change, commit changes.

I will give you known_mistakes.md file and analisys_report_check.json that shows how many mistakes were found.
After your work I will run new detection cycle and give you new analisys_report_check.json, so based on previous context you can add new instructions.

Here are locations of known_mistakes.md file and analisys_report_check.json:
