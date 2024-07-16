from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import openai
from dotenv import load_dotenv
import os

app = FastAPI()

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Enable session handling
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Initial questions
questions = [
    "To gain further understanding, can you please describe your educational experience?",
    "What are your aspirations and higher education goals (e.g., want to study abroad or at elite universities)?",
    "Please describe if there are any financial constraints?"
]

# Options to present after initial questions
final_options = [
    "Would you like a detailed roadmap to achieve your career goals considering your academics, financial status, and study locations?",
    "Do you want personalized career guidance based on your academic performance, financial status, and desired study locations?",
    "Do you need other specific guidance like scholarship opportunities, study programs, or financial planning?",
    "Other"
]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Reset session variables
    request.session.clear()
    request.session['question_index'] = 0
    request.session['user_responses'] = []

    # Render template with introductory message
    return templates.TemplateResponse("chat.html", {"request": request, "intro_message": "Hi I am Naavi, your personal coach and navigator for higher education...😊"})

@app.post("/process_chat")
async def process_chat(request: Request, user_input: str = Form(...)):
    question_index = request.session.get('question_index', 0)
    user_responses = request.session.get('user_responses', [])

    # Ensure to store user input if not the first question
    if question_index > 0:
        user_responses.append(user_input)
        request.session['user_responses'] = user_responses

    if question_index < len(questions):
        next_question = questions[question_index]
        request.session['question_index'] = question_index + 1
        return JSONResponse({'question': next_question})
    else:
        request.session['question_index'] = len(questions)  # Ensure index is at the end
        return JSONResponse({'options': final_options})

@app.post("/process_final_option")
async def process_final_option(request: Request, user_input: str = Form(...)):
    user_responses = request.session.get('user_responses', [])
    user_responses.append(user_input)  # Add the option chosen by the user
    bot_response = await get_ai_response(user_responses)
    return JSONResponse({'response': bot_response})

async def get_ai_response(user_responses):
    messages = [{"role": "user", "content": response} for response in user_responses]

    final_prompt = (
        "Based on the information provided, generate three distinct pathways for achieving the user's educational and career goals. "
        "Each pathway should be clearly separated and include step-by-step guidance on academic focus, extracurricular activities, standardized tests, undergraduate education, gaining relevant experience, financial planning, residency, licensing, and additional tips. "
        "Each step should be detailed and easy to understand. Provide specific resources, examples, and tips to help the user along the way."
    )

    messages.append({"role": "user", "content": final_prompt})

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
            top_p=1
        )
        return completion.choices[0].message['content']
    except openai.error.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail="Sorry, something went wrong with the AI service. Please try again later.")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
