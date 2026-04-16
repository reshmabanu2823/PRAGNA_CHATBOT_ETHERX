"""
Demo/Development mode responses for testing the chatbot without valid API keys.
This allows users to test the UI and functionality while they set up proper API credentials.
"""
import logging
import random

logger = logging.getLogger(__name__)

# Language codes
SUPPORTED_LANGUAGES = ['en', 'hi', 'ta', 'te', 'kn', 'ml', 'mr', 'gu', 'pa', 'bn', 'ur']

# Language names mapping
LANGUAGE_NAMES = {
    'en': 'English',
    'hi': 'हिंदी',
    'ta': 'தமிழ்',
    'te': 'తెలుగు',
    'kn': 'ಕನ್ನಡ',
    'ml': 'മലയാളം',
    'mr': 'मराठी',
    'gu': 'ગુજરાતી',
    'pa': 'ਪੰਜਾਬੀ',
    'bn': 'বাংলা',
    'ur': 'اردو'
}

# Language greetings with extended multilingual responses
GREETINGS = {
    'en': [
        "Hello! 👋 I'm Pragna, your AI assistant. Ask me about any topic!",
        "Hi there! 🎉 Ready to help. What would you like to discuss?",
        "Welcome! 🌟 Let's have a great conversation.",
    ],
    'hi': [
        "नमस्ते! 👋 मैं प्रज्ञा हूँ, आपका AI सहायक। कुछ भी पूछें!",
        "हाय! 🎉 मदद करने के लिए तैयार हूँ। बातचीत करते हैं?",
        "स्वागत है! 🌟 एक बेहतरीन बातचीत करते हैं।",
    ],
    'ta': [
        "வணக்கம்! 👋 நான் ப்ரğனா, உங்கள் AI உதவியாளர். கேளுங்கள்!",
        "ஹாய்! 🎉 உதவ தயாரmon். என்ன பேச விரும்புகிறீர்கள்?",
        "வரவேற்கிறோம்! 🌟 அற்புத உரையாடலுக்கு செல்வோம்।",
    ],
    'te': [
        "నమస్కారం! 👋 నేను ఆలోచన, మీ AI సహాయకుడు. ఏదైనా అడగండి!",
        "హాయ్‌! 🎉 సహాయం చేయడానికి సిద్ధంగా ఉన్నాను. ఏమి చర్చించాలనుకుంటున్నారు?",
        "స్వాగతం! 🌟 ఒక అద్భుత సంభాషణ చేద్దాం।",
    ],
    'kn': [
        "ನಮಸ್ಕಾರ! 👋 ನಾನು ಪ್ರಾಗ್ಞ, ನಿಮ್ಮ AI ಸಹಾಯಕ. ಯಾವುದೇ ಕೇಳಿ!",
        "ಹೇ! 🎉 ಸಹಾಯ ಮಾಡಲು ಸಿದ್ಧವಾಗಿದೆ. ಇನ್ನೆಂ ಚರ್ಚೆ ಮಾಡಲಿ?",
        "ಸ್ವಾಗತ! 🌟 ಒಂದು ಅದ್ಭುತ ಕಥೋಪಕಥನೆ ಮಾಡೋಣ।",
    ],
    'ml': [
        "നമസ്കാരം! 👋 ഞാൻ പ്രാണ, നിങ്ങളുടെ AI സഹായി. എന്തിനെങ്കിലും ചോദിക്കുക!",
        "ഹായ്! 🎉 സഹായിക്കാൻ തയ്യാറാണ്. എന്ത് ചിന്തിച്ച് നിൽക്കാൻ നിങ്ങളായിരിക്കും?",
        "സ്വാഗതം! 🌟 മനോഹരമായ സംഭാഷണം നടത്തേക്കുക.",
    ],
    'mr': [
        "नमस्कार! 👋 मी प्राया, आपले AI सहायक. कुछ पूछा!",
        "हाय! 🎉 मदत करांर तयार आहे. चर्चा करू?",
        "स्वागत! 🌟 छान संभाषण करूया.",
    ],
    'gu': [
        "નમસ્તે! 👋 હું પ્રાન, તમારો AI સહાયક. કોઈ પણ પૂછો!",
        "હાય! 🎉 મદદ કરવા માટે તૈયાર. શું ચર્ચા કરવી છે?",
        "સ્વાગત! 🌟 શાનદાર કથોપકથન કરીએ.",
    ],
    'pa': [
        "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! 👋 ਮੈਂ ਪ੍ਰਾਨਾ, ਤੁਹਾਡਾ AI ਸਹਾਇਕ. ਕੁਝ ਪੁੱਛੋ!",
        "ਹੇ! 🎉 ਮਦਦ ਕਰਨ ਲਈ ਤਿਆਰ. ਕੀ ਚਰਚਾ ਕਰਨੀ ਹੈ?",
        "ਸ੍ਵਾਗਤ! 🌟 ਸ਼ਾਨਦਾਰ ਗੱਲਬਾਤ ਕਰੀਏ।",
    ],
    'bn': [
        "নমস্কার! 👋 আমি প্রাণ, আপনার AI সহায়ক. কিছু জিজ্ঞাসা করুন!",
        "হাই! 🎉 সাহায্য করতে প्রস्तুत. কী আলোচনা করব?",
        "স্বাগতম! 🌟 একটি দুর্দান্ত কথোপকথন করি।",
    ],
    'ur': [
        "السلام علیکم! 👋 میں پ्राना ہوں، آپ کے AI مدد گار۔ کچھ پوچھیں!",
        "ہائے! 🎉 مدد کے لیے تیار۔ کیا بات کریں گے?",
        "خوش آمدید! 🌟 ایک بہترین گفتگو کریں۔",
    ],
}

# Comprehensive demo responses organized by topic
DEMO_KNOWLEDGE_BASE = {
    "blockchain": [
        "Blockchain is a distributed ledger technology that maintains a continuously growing list of records called blocks. Each block contains a cryptographic hash of the previous block, creating an immutable chain. This technology ensures transparency, security, and decentralization by eliminating the need for a central authority.",
        "The most well-known blockchain implementation is Bitcoin, created in 2009. However, blockchain technology extends far beyond cryptocurrency. It's used in supply chain management, smart contracts, healthcare records, voting systems, and many other applications that require secure, transparent record-keeping.",
        "Key features of blockchain include: immutability (once recorded, data is extremely difficult to change), transparency (all participants can view transactions), decentralization (no single point of failure), and security (cryptographic principles). These features make blockchain particularly useful for scenarios requiring trust among multiple parties.",
    ],
    "artificial_intelligence": [
        "Artificial Intelligence (AI) refers to computer systems designed to perform tasks that typically require human intelligence. This includes learning from experience, recognizing patterns, understanding language, and making decisions. AI technology is being applied across industries from healthcare to finance to transportation.",
        "Machine Learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. Deep Learning, a subset of Machine Learning, uses neural networks with multiple layers to process complex data patterns, powering modern applications like image recognition and natural language processing.",
        "Recent advances in AI include Large Language Models like GPT-4, which can understand and generate human-like text. These models are trained on massive amounts of data and can be fine-tuned for specific applications. AI ethics, responsible AI development, and addressing bias in AI systems are increasingly important considerations.",
    ],
    "cloud_computing": [
        "Cloud computing delivers computing services over the internet, including servers, storage, databases, networking, and software. Instead of owning and maintaining physical infrastructure, organizations can rent these services on-demand, paying only for what they use. Major cloud providers include AWS, Microsoft Azure, and Google Cloud.",
        "Cloud services are typically categorized into three models: Infrastructure as a Service (IaaS) for computing resources, Platform as a Service (PaaS) for development tools and databases, and Software as a Service (SaaS) for ready-to-use applications. Each model offers different levels of control and management responsibility.",
        "Benefits of cloud computing include scalability, cost-efficiency, reliability, security, and flexibility. Organizations can quickly scale resources up or down based on demand. However, considerations like data security, compliance, and vendor lock-in need careful evaluation when adopting cloud solutions.",
    ],
    "cybersecurity": [
        "Cybersecurity involves protecting computer systems and networks from unauthorized access, data theft, and malicious attacks. It encompasses various practices including firewalls, encryption, authentication systems, and security awareness training. With increasing digitalization, cybersecurity has become critical for organizations of all sizes.",
        "Common cyber threats include malware, phishing attacks, ransomware, DDoS attacks, and insider threats. A comprehensive security strategy involves multiple layers of defense: preventive measures, detection systems, and incident response procedures. Regular security audits and penetration testing help identify vulnerabilities before they can be exploited.",
        "Best practices for cybersecurity include using strong passwords, enabling multi-factor authentication, keeping software updated, regular backups, employee training, and having an incident response plan. Zero-trust security models, which verify every access attempt, are becoming increasingly important in modern security architectures.",
    ],
    "data_science": [
        "Data Science combines statistics, programming, and domain expertise to extract meaningful insights from data. Data Scientists work with large datasets using tools like Python, R, and SQL to identify patterns, build predictive models, and inform business decisions. The field has become essential for competitive advantage in modern business.",
        "The data science process typically involves problem definition, data collection and cleaning, exploratory data analysis, feature engineering, model selection and training, evaluation, and deployment. Challenges include dealing with incomplete or biased data, choosing appropriate models, and communicating findings to non-technical stakeholders.",
        "Applications of data science include customer segmentation, fraud detection, recommendation systems, predictive maintenance, and healthcare diagnostics. However, ethical considerations around data privacy, algorithmic bias, and responsible AI are crucial. Data scientists must balance accuracy with fairness and transparency.",
    ],
    "web_development": [
        "Web development involves creating and maintaining websites and web applications. Frontend development focuses on user interface and experience using HTML, CSS, and JavaScript. Backend development handles server logic, databases, and APIs. Full-stack developers work on both frontend and backend components.",
        "Modern web development emphasizes responsive design that works across devices, progressive web apps that function offline, and fast loading times. Popular frameworks like React, Vue, and Angular on the frontend, and Node.js, Django, and Flask on the backend simplify development. Version control with Git and proper testing practices are essential.",
        "Web applications today are increasingly complex, requiring attention to performance optimization, security (HTTPS, SQL injection prevention, XSS protection), accessibility standards, and SEO. Cloud deployment, containerization with Docker, and CI/CD pipelines have become standard practices in professional web development.",
    ],
}

# Fallback general responses for topics not in knowledge base
GENERAL_RESPONSES = [
    "That's an interesting question! While I'm in demonstration mode without full API access, I can provide general guidance. For more detailed and accurate information, please get a valid Groq API key and update your backend/.env file.",
    "I appreciate your interest in this topic. In production mode with proper API credentials, I'd be able to provide more comprehensive and personalized responses. Currently, I'm running in development mode for testing purposes.",
    "This is a great question! To get the best and most current responses, I'd recommend setting up a valid API key. You can get one from https://console.groq.com. The chatbot will then use the real Groq LLM for much more capable responses.",
]

# General greeting responses organized by language
GREETING_RESPONSES_MULTILINGUAL = {
    "en": [
        "Hello! 👋 I'm Pragna, an AI assistant. Feel free to ask me about blockchain, AI, cloud computing, cybersecurity, data science, web development, or many other topics!",
        "Hi there! 🎉 Thanks for chatting with me. I'm here to help answer questions and have conversations. What would you like to discuss?",
        "Welcome! 👋 I'm happy to chat with you. Ask me anything!",
    ],
    "hi": [
        "नमस्ते! 👋 मैं प्रज्ञा हूँ, एक AI सहायक। मुझसे ब्लॉकचेन, AI, क्लाउड कंप्यूटिंग, साइबर सुरक्षा, डेटा विज्ञान, वेब विकास या कई अन्य विषयों के बारे में पूछें!",
        "हाय! 🎉 मुझसे बात करने के लिए धन्यवाद। मैं आपके प्रश्नों का उत्तर देने और बातचीत करने के लिए यहाँ हूँ। क्या पूछना चाहते हैं?",
        "स्वागत है! 👋 मुझे आपके साथ बातचीत करना अच्छा लगता है। मुझसे कुछ भी पूछें!",
    ],
    "ta": [
        "வணக்கம்! 👋 நான் ப्रGyaan, ஒரு AI உதவியாளர். ப்blॉcks்chcain, AI, க्cloud कomputing, साइber保সएरता,데이타 வScience, வेb फDevelopment,또는 மேலும் பல விഷയங்களைபற்றி என்னிடம் கேளுங்கள!",
    ],
}

GREETING_RESPONSES = [
    "Hello! 👋 I'm Pragna, an AI assistant. Feel free to ask me about blockchain, AI, cloud computing, cybersecurity, data science, web development, or many other topics. (Running in demo mode - some API features are limited)",
    "Hi there! 🎉 Thanks for chatting with me. I'm here to help answer questions and have conversations. What would you like to discuss?",
    "Welcome! 👋 I'm happy to chat with you. Ask me anything - whether it's about technology, concepts, or just having a conversation!",
]

def _format_response_for_mode(content: str, chat_mode: str, language: str) -> str:
    """
    Format the response based on the selected chat mode.
    
    Args:
        content: The base response content
        chat_mode: The chat mode (general, explain_concepts, generate_ideas, code_assistance, etc.)
        language: The language code
        
    Returns:
        Formatted response string
    """
    import sys
    sys.stderr.write(f"🔴 DEMO FMT: mode={chat_mode} lang={language}\n")
    sys.stderr.flush()
    mode_instructions = {
        "explain_concepts": {
            "en": "📚 **Explanation Mode**: Breaking down the concept into clear, simple parts:\n\n",
            "hi": "📚 **व्याख्या मोड**: अवधारणा को स्पष्ट, सरल भागों में तोड़ना:\n\n",
            "ta": "📚 **விளக்கம் பயன்முறை**: கருத்தை தெளிவான, எளிய பகுதிகளாக பிரிப்பது:\n\n",
            "te": "📚 **వివరణ మోడ్**: కన్సెప్ట్‌ను స్పష్టమైన, సరళ భాగాలుగా విభజించడం:\n\n",
            "kn": "📚 **ವಿವರಣೆ ಮೋಡ್**: ಪರಿಕಲ್ಪನೆಯನ್ನು ಸ್ಪಷ್ಟ, ಸರಳ ಭಾಗಗಳಾಗಿ ವಿಭಜಿಸುವುದು:\n\n",
        },
        "generate_ideas": {
            "en": "💡 **Creative Ideas Mode**: Brainstorming interesting ideas:\n\n",
            "hi": "💡 **रचनात्मक विचार मोड**: दिलचस्प विचारों पर विचार-विमर्श:\n\n",
            "ta": "💡 **படைப்பு ধারণা பயன்முறை**: சுவாரஸ்யமான ধारணைகளை ஆலோசனை செய்வது:\n\n",
            "te": "💡 **సృజనాత్మక ఆइడియాస్ మోడ్**: ఆసక్తికరమైన ఆలోచనలు:\n\n",
            "kn": "💡 **ಸೃಜನಶೀಲ ಆಲೋಚನೆ ಮೋಡ್**: ಆಸಕ್ತಿದಾಯಕ ಆಲೋಚನೆಗಳ ಮೇಲೆ ಚಿಂತನೆ:\n\n",
        },
        "code_assistance": {
            "en": "💻 **Code Mode**: Providing code examples:\n\n",
            "hi": "💻 **कोड मोड**: कोड उदाहरण प्रदान करना:\n\n",
            "ta": "💻 **குறியீடு பயன்முறை**: குறியீடு உதாரணங்கள் வழங்குதல்:\n\n",
            "te": "💻 **కోడ్ మోడ్**: కోడ్ ఉదాహరణలను అందించడం:\n\n",
            "kn": "💻 **ಕೋಡ್ ಮೋಡ್**: ಕೋಡ್ ಉದಾಹರಣೆಗಳನ್ನು ಒದಗಿಸುವುದು:\n\n",
        },
        "creative_writing": {
            "en": "✍️ **Creative Writing Mode**: Crafting a narrative:\n\n",
            "hi": "✍️ **रचनात्मक लेखन मोड**: एक आख्यान बनाना:\n\n",
            "ta": "✍️ **உண்மையான எழுत்து பயன்முறை**: ஒரு கதை உருவாக்குதல்:\n\n",
            "te": "✍️ **క్రియేటివ్ రైటింగ్ మోడ్**: ఒక కథ రూపొందించడం:\n\n",
            "kn": "✍️ **ಸೃಜನಶೀಲ ಬರವಣಿಗೆ ಮೋಡ್**: ಒಂದು ಕಥೆ ರಚಿಸುವುದು:\n\n",
        }
    }
    
    # DEBUG: Log formatting attempt
    logger.debug(f"🎨 _format_response_for_mode() called: chat_mode={chat_mode}, language={language}")
    
    # Get mode prefix if available
    if chat_mode in mode_instructions and language in mode_instructions[chat_mode]:
        prefix = mode_instructions[chat_mode][language]
        logger.debug(f"✅ Mode prefix found: {prefix[:50]}...")
    else:
        prefix = ""
        logger.debug(f"⚠️ No prefix for mode={chat_mode}, language={language}")
    
    formatted = prefix + content
    logger.debug(f"📖 Formatted response length: {len(formatted)} chars")
    return formatted

def get_demo_response(user_message: str, language: str = "en", chat_mode: str = "general") -> str:
    """
    Generate a demo response based on the user's message, language, and chat mode.
    Searches for keywords and provides relevant information from the knowledge base.
    
    Args:
        user_message: The user's input message
        language: Language code (en, hi, ta, te, kn, ml, mr, gu, pa, bn, ur)
        chat_mode: Chat mode (general, explain_concepts, generate_ideas, code_assistance, creative_writing, etc.)
        
    Returns:
        A demo response string formatted for the selected language and mode
    """
    logger.info(f"📋 Using demo response in {LANGUAGE_NAMES.get(language, 'English')} ({language}), mode: {chat_mode}")
    
    # Normalize language code
    language = language.lower() if language else "en"
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    
    message_lower = user_message.lower()
    
    # Check for greetings
    greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy", 
                 "नमस्ते", "हेलो", "வணக்கம்", "హలో", "ನಮಸ್ಕಾರ", "നമസ്കാരം", "नमस्कार", "સ્વાગત", "ਸਤਿ", "नमस्कार", "السلام"]
    
    if any(greeting.lower() in message_lower for greeting in greetings) and len(user_message) < 50:
        logger.debug(f"✅ Greeting detected, returning greeting for language={language}")
        # Return greeting in selected language WITH mode formatting applied
        greeting_response = random.choice(GREETINGS.get(language, GREETINGS["en"]))
        logger.debug(f"📝 Selected greeting: '{greeting_response[:50]}...'")
        # Apply mode formatting to greeting
        greeting_response = _format_response_for_mode(greeting_response, chat_mode, language)
        logger.debug(f"✨ After formatting: '{greeting_response[:50]}...'")
        return greeting_response
    
    # Check for specific topics
    topic_keywords = {
        "blockchain": ["blockchain", "bitcoin", "crypto", "distributed ledger", "ethereum", "smart contract", "web3"],
        "artificial_intelligence": ["ai", "artificial intelligence", "machine learning", "deep learning", "neural network", "llm", "gpt"],
        "cloud_computing": ["cloud", "aws", "azure", "google cloud", "iaas", "paas", "saas"],
        "cybersecurity": ["cybersecurity", "security", "hack", "breach", "firewall", "encryption", "malware", "phishing"],
        "data_science": ["data science", "data analytics", "machine learning", "predictive", "analysis", "statistics", "dataset"],
        "web_development": ["web development", "website", "html", "css", "javascript", "frontend", "backend", "full-stack"],
    }
    
    # Find matching topic
    for topic, keywords in topic_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            logger.debug(f"✅ Topic detected: {topic}")
            response = random.choice(DEMO_KNOWLEDGE_BASE[topic])
            logger.debug(f"📝 Base response: '{response[:50]}...'")
            # Format based on chat mode
            response = _format_response_for_mode(response, chat_mode, language)
            logger.debug(f"✨ After formatting: '{response[:50]}...'")
            
            # Add demo note
            if language == "en":
                response += "\n\n💡 *Note: This is a demo response. For live, current information and AI-powered analysis, please configure a valid Groq API key.*"
            elif language == "hi":
                response += "\n\n💡 *नोट: यह एक डेमो प्रतिक्रिया है। लाइव, वर्तमान जानकारी और एआई-संचालित विश्लेषण के लिए, कृपया एक वैध Groq API कुंजी कॉन्फ़िगर करें।*"
            elif language == "ta":
                response += "\n\n💡 *குறிப்பு: இது ஒரு டெமோ பதிலாகும். நேரடி, தற்போதைய தகவல் மற்றும் AI-வளா பகுப்பாய்விற்கு, தயவுசெய்து ஒரு செல்லுபடியாகும் Groq API விசையை உள்ளமைக்கவும்.*"
            
            return response
    
    # Default general response
    logger.debug(f"⚠️ No topic matched, using default response for language={language}")
    if language == "en":
        response = random.choice(GENERAL_RESPONSES)
    else:
        response = f"I appreciate your question about '{user_message}'. While I'm in demo mode, I can try to help. For better responses, please set up a valid Groq API key."
    
    logger.debug(f"📝 Default response: '{response[:50]}...'")
    # Format based on chat mode
    response = _format_response_for_mode(response, chat_mode, language)
    logger.debug(f"✨ After formatting: '{response[:50]}...'")
    
    if language == "en":
        response += f"\n\n📝 To enable full AI responses, please:\n1. Visit https://console.groq.com\n2. Get your API key\n3. Update backend/.env with GROQ_API_KEY=your_key\n4. Restart the server"
    
    return response

def is_demo_mode_available() -> bool:
    """Check if demo mode is enabled"""
    try:
        import config
        return config.DEVELOPMENT_MODE
    except:
        return False

def generate_debug_response(error_details: str) -> str:
    """Generate a helpful response when demo mode isn't enabled but we still can't reach the API"""
    return (
        "⚠️ **API Connection Error**\n\n"
        f"Details: {error_details}\n\n"
        "**To fix this:**\n"
        "1. Get a Groq API key: https://console.groq.com\n"
        "2. Update `backend/.env` with your API key:\n"
        "   `GROQ_API_KEY=your_key_here`\n"
        "3. Restart the backend server\n"
        "4. (Optional) Enable demo mode: `DEVELOPMENT_MODE=True` in .env\n\n"
        "**Need help?** The demo mode provides mock responses for testing while you set up the API."
    )
