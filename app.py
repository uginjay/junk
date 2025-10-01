from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import openai
import requests
import json

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')
SEARCHAPI_API_KEY = os.getenv('SEARCHAPI_API_KEY')

def extract_facts(text):
    """Extract key facts from text using OpenAI"""
    try:
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Вы помощник для извлечения фактов из текста. Извлеките основные утверждения и факты, которые требуют проверки. Верните список фактов в формате JSON: {\"facts\": [\"факт 1\", \"факт 2\", ...]}"},
                {"role": "user", "content": f"Извлеките проверяемые факты из следующего текста:\n\n{text}"}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        # Try to parse JSON from response
        try:
            result = json.loads(content)
            return result.get('facts', [])
        except json.JSONDecodeError:
            # If not valid JSON, try to extract facts from text
            lines = content.strip().split('\n')
            facts = [line.strip('- ').strip() for line in lines if line.strip() and line.strip().startswith('-')]
            return facts if facts else [content]
    except Exception as e:
        print(f"Error extracting facts: {e}")
        return []

def search_web(query):
    """Search the web using SearchAPI.io"""
    try:
        url = "https://www.searchapi.io/api/v1/search"
        params = {
            "api_key": SEARCHAPI_API_KEY,
            "engine": "google",
            "q": query,
            "num": 5
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Extract organic results
            organic_results = data.get('organic_results', [])
            for result in organic_results[:3]:  # Top 3 results
                results.append({
                    'title': result.get('title', ''),
                    'snippet': result.get('snippet', ''),
                    'link': result.get('link', '')
                })
            
            return results
        else:
            return []
    except Exception as e:
        print(f"Error searching web: {e}")
        return []

def verify_fact(fact, search_results):
    """Verify a fact using search results and OpenAI"""
    try:
        client = openai.OpenAI(api_key=openai.api_key)
        
        # Prepare search context
        context = "\n\n".join([
            f"Источник: {r['title']}\n{r['snippet']}\nURL: {r['link']}"
            for r in search_results
        ])
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Вы эксперт по проверке фактов. Проанализируйте утверждение на основе предоставленных источников и определите: ВЕРНО, НЕВЕРНО, или ТРЕБУЕТ УТОЧНЕНИЯ. Предоставьте краткое объяснение."},
                {"role": "user", "content": f"Утверждение: {fact}\n\nНайденная информация из интернета:\n{context}\n\nПроверьте это утверждение и предоставьте вердикт (ВЕРНО/НЕВЕРНО/ТРЕБУЕТ УТОЧНЕНИЯ) и краткое объяснение."}
            ],
            temperature=0.3
        )
        
        verification = response.choices[0].message.content
        
        # Determine verdict
        verdict = "ТРЕБУЕТ УТОЧНЕНИЯ"
        if "ВЕРНО" in verification.upper() and "НЕВЕРНО" not in verification.upper():
            verdict = "ВЕРНО"
        elif "НЕВЕРНО" in verification.upper():
            verdict = "НЕВЕРНО"
        
        return {
            'verdict': verdict,
            'explanation': verification,
            'sources': search_results
        }
    except Exception as e:
        print(f"Error verifying fact: {e}")
        return {
            'verdict': 'ОШИБКА',
            'explanation': f'Ошибка при проверке: {str(e)}',
            'sources': []
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def check_facts():
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Текст не предоставлен'}), 400
        
        # Step 1: Extract facts
        facts = extract_facts(text)
        
        if not facts:
            return jsonify({'error': 'Не удалось извлечь факты из текста'}), 400
        
        # Step 2: Search and verify each fact
        results = []
        for fact in facts:
            search_results = search_web(fact)
            verification = verify_fact(fact, search_results)
            
            results.append({
                'fact': fact,
                'verdict': verification['verdict'],
                'explanation': verification['explanation'],
                'sources': verification['sources']
            })
        
        return jsonify({
            'original_text': text,
            'facts_checked': len(facts),
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
