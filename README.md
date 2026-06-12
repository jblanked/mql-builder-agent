# MQL Builder Agent
A Python GUI AI agent that creates, edits, and compiles MetaTrader4/Metatrader5 (MQL4/MQL5) expert advisors, scripts, and indicators.

## Requirements
- Python 3.12+
- MetaTrader 4 or 5 installed
- Windows OS

## Installation
```bash
# Clone the repository and set up the environment
git clone https://github.com/jblanked/mql-builder-agent.git
cd mql-builder-agent
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
```

Then configure `api_keys.py` with your DeepSeek (preferred) and/or OpenAI API key
```bash
# create api_keys.py
ni api_keys.py

# in a text editor
OPENAI_API_KEY = "your_openai_api_key_here"
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"
```

The agent uses `deepseek-v4-flash` as the default model. You can change this in `llm_providers.py` if you want to use a different model or switch to OpenAI's `gpt-5.4-mini` (note that OpenAI's models may have much higher cost compared to DeepSeek).

## Usage
```bash
# Run the agent with the GUI
python app.py

# or use command line for quick tasks
python main.py --topic "Write an MQL5 EA that implements a moving average crossover strategy"

# edit an existing file
python main.py --topic "Change the stop loss to 50 pips after a 20/50 simple moving average crossover" --path "path/to/your/file.mq5"
```