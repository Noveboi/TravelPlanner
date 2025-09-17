# Travel Itinerary Planner

Create a balanced and tailored-to-you travel itinerary with the help of AI.

Developed with [LangGraph](https://langchain-ai.github.io/langgraph/), this system utilizes the agentic workflow capabilities of the framework to build a multi-agent chain-of-responsibility that starts with a user's travel request and ends with a complete travel itinerary.

## Agents

Below are the agents used in the workflow of the system. Each agent has a single responsibility.

### Trip Analyzer

Generates a profile for the trip such as assessing group dynamics (travelling solo, family, couple, ...) and parsing the travel style/preference of the user  

### Destination Researcher

Responsible for gathering information about a specific destination, including weather patterns, cost indicators, seasonal considerations and more...

This agent heavily uses external third-party APIs to get up-to-date information on places and the destination in general. 

### Activity Finder

Discovers and categorizes activities for the trip such as:

- Must-see attractions
- Hidden gems

All while taking into account the user's travel profile.

### Budgeting

Optimizes spending across categories based on the user's profile. This includes:

- Accommodation recommendations (location vs cost)
- Transportation cost analysis
- Activity prioritization based on user's given budget

### Itinerary Builder

Creates logical day-by-day plans for the whole trip. Tailors the itinerary based on:

- Minimizing travel time
- Managing relaxed and intense days
- Meal planning

## Tools

External APIs and tools are used to gather up-to-date and relevant data and information for the constructinon of the itinerary