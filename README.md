AI-Powered Dietary Assistant Agent is a fully autonomous multi-agent dietary assistant using LangGraph to orchestrate a pipeline of 
specialised AI agents. The system takes a user’s medical profile and pantry inventory as inputs and runs them through a 
Nutrition Agent (Serper + Gemini via Locus) that searches the web for condition-specific dish recommendations and nutritional data,
a Recipe Agent that generates step-by step recipes and finds relevant Youtube tutorials,
and an Order Agent that autonomously browses Blinkit and Zepto using BrowserBase and Playwright to add missing ingredients to the cart 
to place Cash on Delivery Orders.
The application features a Streamlit UI with persistent session date, medical record analysis via Gemini and a real-time pantry tracker- 
all together.       
