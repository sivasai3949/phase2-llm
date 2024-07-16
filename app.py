from flask import Flask, render_template, request, session, jsonify
import cohere
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Set up Cohere API client
cohere_api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(cohere_api_key)

# Set secret key for session management
app.secret_key = os.getenv("SECRET_KEY")

# Updated questions for the user
questions = [
    "Please introduce about yourself with basic background information such where are you based, language, education",
    "To gain further understanding can you please describe your educational experience",
    "What are your aspirations, and higher education Goals (want to study abroad or study at elite universities?",
    "Please describe if there are any financial constraints?"
]

# Options presented after initial questions
final_options = [
    "Would you like a detailed roadmap to achieve your career goals considering your academics, financial status, and study locations?",
    "Do you want personalized career guidance based on your academic performance, financial status, and desired study locations?",
    "Do you need other specific guidance like scholarship opportunities, study programs, or financial planning?",
    "Other"
]

# Home route to start the chatbot
@app.route('/')
def home():
    session.clear()  # Clear session to start fresh
    session['question_index'] = 0  # Initialize question index
    session['user_responses'] = []  # Initialize user responses list
    return render_template('home.html', initial_question=questions[0])

# Endpoint to process user input
@app.route('/process_chat', methods=['POST'])
def process_chat():
    user_input = request.form.get('user_input')
    
    if user_input:
        question_index = session.get('question_index', 0)
        user_responses = session.get('user_responses', [])
        user_responses.append(user_input)
        session['user_responses'] = user_responses
        
        if question_index < len(questions):
            question_index += 1
            session['question_index'] = question_index
            
            if question_index < len(questions):
                return jsonify({'question': questions[question_index]})
            else:
                return jsonify({'options': final_options})
        
        else:
            try:
                detailed_prompt = create_detailed_prompt(user_responses)
                bot_response = get_cohere_response(detailed_prompt)
                return jsonify({'response': bot_response})
            except cohere.error.CohereAPIError as e:
                app.logger.error(f"Cohere API error: {str(e)}")
                return jsonify({'error': 'Sorry, something went wrong with the AI service. Please try again later.'}), 500
    
    return jsonify({'error': 'Invalid input'}), 400

# Function to create a detailed prompt based on user responses
def create_detailed_prompt(user_responses):
    prompt = "Based on the following information provided by the user:\n"
    prompt += f"1. Basic Background Information: {user_responses[0]}\n"
    prompt += f"2. Educational Experience: {user_responses[1]}\n"
    prompt += f"3. Aspirations and Higher Education Goals: {user_responses[2]}\n"
    prompt += f"4. Financial Constraints: {user_responses[3]}\n"
    prompt += "Please generate a detailed roadmap or personalized career guidance."
    return prompt

# Function to get response from Cohere API
def get_cohere_response(input_text):
    try:
        response = co.generate(
            model='command-nightly',
            prompt=input_text,
            max_tokens=300,
            temperature=0.9,
            k=0,
            p=0.75,
            stop_sequences=[],
            return_likelihoods='NONE'
        )
        return response.generations[0].text.strip()
    
    except cohere.error.CohereAPIError as e:
        raise RuntimeError(f"Error from Cohere API: {str(e)}")  # Propagate the error for logging and handling

if __name__ == '__main__':
    app.run(debug=True)
