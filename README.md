# Travel Itinerary Planner

Create balanced, personalized travel plans with AI. This app scouts destinations, landmarks, events, establishments, and accommodations, then assembles day-by-day itineraries tailored to your budget, interests, and trip duration. It scores places, balances themes and activities, and outputs clear itineraries you can use immediately.

## Getting Started

### 1 - Clone the repository
```shell
git clone https://github.com/Noveboi/TravelPlanner
```

### 2 - Create a virtual environment
Once you've cloned the repository. Navigate to the root with your terminal and create a virtual environment

```shell
python -m venv .venv
```

### 3 - Activate your virtual environment
```shell
# On Mac/Linux
source .venv/bin/activate
```

```shell
# On Windows using Powershell
source .venv\Scripts\Activate.ps1
```

```shell
# On Windows using Bash (e.g: Typically a VS Code or PyCharm terminal)
source .venv/Scripts/activate
```

### 4 - Install Packages
After you've set up your virtual environment, install the packages declared in **requirements.txt**:

```shell
pip install -r requirements.txt
```

### 5 - Setup API Keys
For the application to run, you need to set some API keys and set then in a `.env` file. First, create the .env file:

```dotenv
TAVILY_API_KEY=<YOUR-KEY-HERE>
OPENAI_API_KEY=<YOUR-KEY-HERE>
FOURSQUARE_API_KEY=<YOUR-KEY-HERE>
```

The keys you'll need are from:

- [Tavily](https://www.tavily.com/): Create a free account, and you'll get an API key.
- [OpenRouter](https://openrouter.ai): Create a free account, then go [here](https://openrouter.ai/settings/keys) to get an API key. If you plan to use some other LLM model (locally or not OpenRouter), then you can configure accordingly.
- [Foursquare](https://foursquare.com/developer/): Create a free account and go to the [developer console](https://foursquare.com/developers/home). Start by creating a new project, then navigate to the project and click "Generate API Key", then generate a "**Service API Key**" and copy it.

After you've added all three API keys, you are ready.

### 6 - Run the app
```shell
python main.py
```
