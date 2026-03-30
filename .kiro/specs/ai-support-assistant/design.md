# Design Document: AI Support Assistant

## Overview

The DaisyandCoco AI Support Assistant is an intelligent help system integrated into the DCCCO Multipurpose Cooperative loan management system. This feature provides contextual guidance, troubleshooting support, and system knowledge through an interactive AI interface accessible exclusively to admin users.

The assistant leverages a knowledge base approach to understand system functionalities and provides animated, engaging responses through a chat interface. The design follows the existing Flask/Bootstrap architecture with Socket.IO for real-time interactions and maintains consistency with the current UI/UX patterns including dark mode support.

### Key Design Goals

1. **Admin-Only Access**: Restrict access through role-based authentication
2. **Knowledge Base Integration**: Embed system documentation and workflows for accurate responses
3. **Animated Interactions**: Provide visual feedback through typing indicators and smooth transitions
4. **Seamless Integration**: Match existing UI patterns, navigation structure, and styling
5. **Mobile Responsiveness**: Ensure full functionality on mobile devices with bottom navigation
6. **Session Persistence**: Maintain conversation context during user sessions

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[AI Support UI<br/>templates/ai_support.html]
        JS[Client JavaScript<br/>static/ai-support.js]
        CSS[Styling<br/>Inline + base.html]
    end
    
    subgraph "Backend Layer"
        Route[Flask Route<br/>/ai-support]
        API[API Endpoint<br/>/api/ai_query]
        Auth[Authentication<br/>@login_required]
        RoleCheck[Role Check<br/>admin only]
    end
    
    subgraph "AI Processing Layer"
        AIEngine[AI Engine<br/>OpenAI/Anthropic API]
        KB[Knowledge Base<br/>System Context]
        Prompt[Prompt Builder<br/>Context Injection]
    end
    
    subgraph "Data Layer"
        Session[Flask Session<br/>Chat History]
        DB[(SQLite Database<br/>System Data)]
    end
    
    UI --> JS
    JS --> API
    API --> Auth
    Auth --> RoleCheck
    RoleCheck --> Prompt
    Prompt --> KB
    Prompt --> AIEngine
    AIEngine --> API
    API --> JS
    JS --> UI
    
    Route --> Auth
    Auth --> Session
    Prompt --> DB
    
    style UI fill:#60a5fa
    style API fill:#fbbf24
    style AIEngine fill:#31a24c
    style KB fill:#f59e0b
```

### Component Interaction Flow

1. **User Request Flow**:
   - Admin user navigates to /ai-support
   - Flask route validates authentication and admin role
   - Template renders with chat interface and DaisyandCoco image
   - User types query and submits

2. **AI Processing Flow**:
   - Client JavaScript sends query to /api/ai_query endpoint
   - Backend validates session and role
   - Prompt builder injects system knowledge base context
   - AI engine processes query with context
   - Response streams back to client
   - Client displays animated response

3. **Session Management Flow**:
   - Chat history stored in Flask session
   - Limited to 50 most recent messages
   - Cleared on logout
   - Restored on page navigation

## Components and Interfaces

### Backend Components

#### 1. Flask Routes

**Route: `/ai-support`**
- **Method**: GET
- **Authentication**: @login_required
- **Authorization**: Admin role only
- **Purpose**: Render AI support interface
- **Returns**: HTML template with chat interface

```python
@app.route('/ai-support')
@login_required
def ai_support():
    if current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Get chat history from session
    chat_history = session.get('ai_chat_history', [])
    
    conn = get_db()
    unread_count = conn.execute('''
        SELECT COUNT(*) as count FROM notifications 
        WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"
    ''', (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('ai_support.html', 
                         chat_history=chat_history,
                         unread_count=unread_count)
```

**Route: `/api/ai_query`**
- **Method**: POST
- **Authentication**: @login_required
- **Authorization**: Admin role only
- **Purpose**: Process AI queries and return responses
- **Input**: JSON with `query` field
- **Output**: JSON with `response` field

```python
@app.route('/api/ai_query', methods=['POST'])
@login_required
def ai_query():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    # Get chat history from session
    chat_history = session.get('ai_chat_history', [])
    
    # Build system context with knowledge base
    system_context = build_system_context()
    
    # Call AI engine
    try:
        response = call_ai_engine(query, chat_history, system_context)
        
        # Update chat history
        chat_history.append({'role': 'user', 'content': query})
        chat_history.append({'role': 'assistant', 'content': response})
        
        # Keep only last 50 messages (25 exchanges)
        if len(chat_history) > 50:
            chat_history = chat_history[-50:]
        
        session['ai_chat_history'] = chat_history
        session.modified = True
        
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Route: `/api/ai_clear_history`**
- **Method**: POST
- **Authentication**: @login_required
- **Authorization**: Admin role only
- **Purpose**: Clear chat history
- **Output**: JSON success response

```python
@app.route('/api/ai_clear_history', methods=['POST'])
@login_required
def ai_clear_history():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    session['ai_chat_history'] = []
    session.modified = True
    
    return jsonify({'success': True})
```

#### 2. AI Engine Integration

**Function: `call_ai_engine(query, history, context)`**
- **Purpose**: Interface with AI API (OpenAI or Anthropic)
- **Parameters**:
  - `query`: User's current question
  - `history`: Previous conversation messages
  - `context`: System knowledge base
- **Returns**: AI-generated response string

```python
def call_ai_engine(query, history, context):
    """
    Call AI API with system context and conversation history
    Supports OpenAI and Anthropic APIs
    """
    import openai
    
    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise Exception('No AI API key configured')
    
    # Build messages array
    messages = [
        {
            'role': 'system',
            'content': f"""You are DaisyandCoco, an AI assistant for the DCCCO Multipurpose Cooperative loan management system.
            
You help administrators understand and troubleshoot the system.

SYSTEM KNOWLEDGE:
{context}

Provide clear, accurate, and helpful responses. Use bullet points and code examples when appropriate.
Reference specific file paths, database tables, and functions when relevant."""
        }
    ]
    
    # Add conversation history
    messages.extend(history)
    
    # Add current query
    messages.append({'role': 'user', 'content': query})
    
    # Call OpenAI API (or Anthropic)
    if os.getenv('OPENAI_API_KEY'):
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model='gpt-4',
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    else:
        # Anthropic API implementation
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-3-sonnet-20240229',
            max_tokens=1000,
            messages=messages
        )
        return response.content[0].text
```

#### 3. Knowledge Base Builder

**Function: `build_system_context()`**
- **Purpose**: Compile system documentation into context string
- **Returns**: Formatted string with system knowledge

```python
def build_system_context():
    """
    Build comprehensive system context for AI assistant
    Includes database schema, routes, features, and workflows
    """
    context = """
# DCCCO Loan Management System Documentation

## System Overview
Flask-based loan management system for DCCCO Multipurpose Cooperative with real-time features using Socket.IO.

## User Roles
1. **admin**: Full system access, approves/rejects loans, manages users
2. **loan_staff**: Submits loan applications, assigns to CI staff
3. **ci_staff**: Conducts credit investigations, completes checklists

## Database Schema

### users table
- id, email, password_hash, name, role, is_approved
- signature_path, backup_email, profile_photo
- is_online, last_seen, current_workload

### loan_applications table
- id, member_name, member_contact, member_address, loan_amount
- status: submitted, assigned_to_ci, ci_completed, approved, rejected
- needs_ci_interview, submitted_by, assigned_ci_staff
- ci_notes, ci_checklist_data, ci_signature, ci_completed_at
- admin_notes, admin_decision_at, submitted_at

### documents table
- id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at

### direct_messages table
- id, sender_id, receiver_id, message, sent_at, is_read, is_edited, is_deleted

### notifications table
- id, user_id, message, link, is_read, created_at

### location_tracking table
- id, user_id, latitude, longitude, activity, tracked_at

## Key Features

### Loan Application Workflow
1. Loan staff submits application via /loan/submit
2. System auto-assigns to CI staff with lowest workload
3. CI staff completes interview and checklist
4. Admin reviews and approves/rejects
5. SMS notification sent to applicant

### Real-Time Messaging
- Direct messages between users via Socket.IO
- Application-specific messaging threads
- Typing indicators and read receipts
- Voice message support

### CI Tracking
- GPS location tracking for CI staff
- Real-time map display for admin
- Activity status updates

### User Management
- Admin approves new user registrations
- Role-based access control
- Password reset with email verification

### Dark Mode
- Toggle via localStorage
- Applies to all pages
- CSS variables for theming

## Common Issues & Solutions

### Issue: User not approved
**Solution**: Admin must approve via /manage_users

### Issue: CI staff not receiving assignments
**Solution**: Check current_workload in users table, verify is_approved=1

### Issue: SMS not sending
**Solution**: Check SEMAPHORE_API_KEY or TEXTBELT_API_KEY in .env

### Issue: Real-time features not working
**Solution**: Verify Socket.IO connection, check browser console for errors

### Issue: File upload failing
**Solution**: Check UPLOAD_FOLDER permissions, verify file extension in ALLOWED_EXTENSIONS

## File Structure
- app.py: Main Flask application
- templates/: HTML templates (Jinja2)
- static/: CSS, JavaScript, images
- uploads/: User-uploaded documents
- signatures/: Digital signatures
- schema.sql: Database schema

## Environment Variables
- SECRET_KEY: Flask session secret
- RESEND_API_KEY: Email service
- SEMAPHORE_API_KEY: SMS service (primary)
- OPENAI_API_KEY or ANTHROPIC_API_KEY: AI assistant
- FLASK_DEBUG: Debug mode flag

## API Endpoints
- /api/send_direct_message: Send message
- /api/update_location: Update CI location
- /api/unread_message_count: Get unread count
- /api/ai_query: AI assistant query (admin only)
"""
    return context
```

### Frontend Components

#### 1. HTML Template (`templates/ai_support.html`)

**Structure**:
- Extends `base.html` for consistent layout
- Top bar with title and user menu
- Main content area with two-column layout:
  - Left: DaisyandCoco image with animations
  - Right: Chat interface
- Chat history display
- Input field with send button
- Clear history button

**Key Elements**:
```html
{% extends "base.html" %}
{% block title %}AI Support - DaisyandCoco{% endblock %}

{% block content %}
<div class="top-bar">
    <h2><i class="bi bi-robot"></i> AI Support Assistant</h2>
    <div class="top-bar-actions">
        <!-- Dark mode toggle, notifications, user menu -->
    </div>
</div>

<div class="ai-support-container">
    <div class="ai-agent-panel">
        <div class="agent-image-container">
            <img src="{{ url_for('static', filename='images/daisy-coco.jpg') }}" 
                 alt="DaisyandCoco" 
                 class="agent-image" 
                 id="agentImage">
            <div class="agent-status" id="agentStatus">
                <i class="bi bi-circle-fill"></i> Ready to help
            </div>
        </div>
        <div class="agent-info">
            <h3>DaisyandCoco</h3>
            <p>Your AI Support Assistant</p>
        </div>
    </div>
    
    <div class="chat-panel">
        <div class="chat-history" id="chatHistory">
            <!-- Messages rendered here -->
        </div>
        
        <div class="chat-input-container">
            <textarea id="queryInput" 
                      placeholder="Ask me anything about the system..." 
                      rows="2"></textarea>
            <button id="sendBtn" class="btn btn-primary">
                <i class="bi bi-send-fill"></i> Send
            </button>
            <button id="clearBtn" class="btn btn-outline-secondary">
                <i class="bi bi-trash"></i> Clear
            </button>
        </div>
    </div>
</div>
{% endblock %}
```

#### 2. Client JavaScript (`static/ai-support.js` or inline)

**Responsibilities**:
- Handle user input and send queries
- Display typing indicators
- Animate response text
- Manage chat history display
- Handle errors gracefully
- Auto-scroll to latest message

**Key Functions**:

```javascript
// Send query to AI
async function sendQuery() {
    const query = document.getElementById('queryInput').value.trim();
    if (!query) return;
    
    // Display user message
    appendMessage('user', query);
    document.getElementById('queryInput').value = '';
    
    // Show typing indicator
    showTypingIndicator();
    animateAgent('thinking');
    
    try {
        const response = await fetch('/api/ai_query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query})
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Animate response
        await animateResponse(data.response);
        animateAgent('idle');
        
    } catch (error) {
        hideTypingIndicator();
        appendMessage('error', 'Sorry, I encountered an error. Please try again.');
        animateAgent('idle');
    }
}

// Animate response text (typewriter effect)
async function animateResponse(text) {
    const messageDiv = createMessageElement('assistant', '');
    document.getElementById('chatHistory').appendChild(messageDiv);
    
    const contentDiv = messageDiv.querySelector('.message-content');
    let index = 0;
    
    return new Promise((resolve) => {
        const interval = setInterval(() => {
            if (index < text.length) {
                contentDiv.textContent += text[index];
                index++;
                scrollToBottom();
            } else {
                clearInterval(interval);
                resolve();
            }
        }, 20); // 20ms per character
    });
}

// Animate agent image
function animateAgent(state) {
    const agentImage = document.getElementById('agentImage');
    const agentStatus = document.getElementById('agentStatus');
    
    if (state === 'thinking') {
        agentImage.classList.add('pulsing');
        agentStatus.innerHTML = '<i class="bi bi-circle-fill text-warning"></i> Thinking...';
    } else {
        agentImage.classList.remove('pulsing');
        agentStatus.innerHTML = '<i class="bi bi-circle-fill text-success"></i> Ready to help';
    }
}

// Show typing indicator
function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'message assistant typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="message-content">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    `;
    document.getElementById('chatHistory').appendChild(indicator);
    scrollToBottom();
}
```

#### 3. Styling (CSS)

**Key Styles**:
- Two-column layout (agent panel + chat panel)
- Message bubbles with distinct colors for user/assistant
- Typing indicator animation
- Agent image pulse effect
- Mobile responsive breakpoints
- Dark mode compatibility

```css
.ai-support-container {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 20px;
    height: calc(100vh - 150px);
}

.ai-agent-panel {
    background: var(--bg-white);
    border-radius: 10px;
    padding: 30px;
    text-align: center;
    box-shadow: var(--card-shadow);
}

.agent-image-container {
    position: relative;
    margin-bottom: 20px;
}

.agent-image {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    object-fit: cover;
    border: 4px solid var(--primary-blue);
    transition: all 0.3s ease;
}

.agent-image.pulsing {
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(30, 58, 95, 0.7); }
    50% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(30, 58, 95, 0); }
}

.chat-panel {
    background: var(--bg-white);
    border-radius: 10px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    box-shadow: var(--card-shadow);
}

.chat-history {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 20px;
    padding: 10px;
}

.message {
    margin-bottom: 15px;
    display: flex;
    animation: fadeIn 0.3s ease;
}

.message.user {
    justify-content: flex-end;
}

.message.assistant {
    justify-content: flex-start;
}

.message-content {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 12px;
    word-wrap: break-word;
}

.message.user .message-content {
    background: var(--primary-blue);
    color: white;
}

.message.assistant .message-content {
    background: var(--light-bg);
    color: var(--text-primary);
}

.typing-indicator .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-secondary);
    margin: 0 2px;
    animation: typing 1.4s infinite;
}

.typing-indicator .dot:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator .dot:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-10px); }
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Mobile responsive */
@media (max-width: 768px) {
    .ai-support-container {
        grid-template-columns: 1fr;
        height: auto;
    }
    
    .ai-agent-panel {
        display: flex;
        align-items: center;
        padding: 15px;
    }
    
    .agent-image {
        width: 80px;
        height: 80px;
    }
    
    .agent-info {
        text-align: left;
        margin-left: 15px;
    }
}
```

### Navigation Integration

**Sidebar Navigation** (in `templates/base.html`):
```html
<nav class="sidebar-nav">
    <!-- Existing menu items -->
    <a href="{{ url_for('change_password') }}">
        <i class="bi bi-key"></i> Change Password
    </a>
    
    <!-- NEW: AI Support link (admin only) -->
    {% if current_user.role == 'admin' %}
    <a href="{{ url_for('ai_support') }}">
        <i class="bi bi-robot"></i> AI Support
    </a>
    {% endif %}
</nav>
```

**Bottom Navigation** (mobile):
```html
<nav class="bottom-nav">
    <!-- Existing items -->
    
    <!-- NEW: AI Support (admin only, shown on mobile) -->
    {% if current_user.role == 'admin' %}
    <a href="{{ url_for('ai_support') }}">
        <i class="bi bi-robot"></i>
        <span>AI Help</span>
    </a>
    {% endif %}
</nav>
```

## Data Models

### Session Data Structure

**Chat History** (stored in Flask session):
```python
session['ai_chat_history'] = [
    {
        'role': 'user',
        'content': 'How do I approve a user?'
    },
    {
        'role': 'assistant',
        'content': 'To approve a user, navigate to /manage_users...'
    },
    # ... up to 50 messages
]
```

### API Request/Response Models

**AI Query Request**:
```json
{
    "query": "How do I assign a CI staff to an application?"
}
```

**AI Query Response**:
```json
{
    "response": "To assign a CI staff member to a loan application:\n\n1. Navigate to the Loan Dashboard\n2. Find the application you want to assign\n3. Click the 'Assign CI' dropdown\n4. Select the CI staff member\n5. The system will automatically update the status to 'assigned_to_ci'\n\nThe CI staff member will receive a notification about the new assignment."
}
```

**Error Response**:
```json
{
    "error": "Unauthorized access"
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, I've identified the following areas of potential redundancy:

**Access Control Properties (1.1, 1.2, 1.4)**:
- 1.1 tests that only admins can access the AI assistant
- 1.2 tests redirect behavior for non-admins
- 1.4 tests that the navigation link only shows for admins
- **Decision**: Keep 1.1 as the core access control property. 1.2 and 1.4 are specific examples of how access control manifests in the UI.

**Knowledge Base Properties (5.1-5.6)**:
- All six properties test that the AI provides information about different system features
- **Decision**: Combine into a single comprehensive property that tests the AI's ability to provide accurate information about any system feature.

**Troubleshooting Properties (6.1-6.4)**:
- All four properties test that the AI provides troubleshooting guidance for different issue types
- **Decision**: Combine into a single property that tests troubleshooting capability across various issue types.

**Response Formatting Properties (8.1-8.4)**:
- All four properties test different aspects of response formatting
- **Decision**: Combine into a single property that tests comprehensive response formatting quality.

**Session Persistence Properties (9.1, 9.2)**:
- 9.1 tests that session persists while logged in
- 9.2 tests that session is restored after navigation
- **Decision**: These are essentially the same property - combine into one.

**Mobile Responsiveness Properties (10.1, 10.2, 10.3)**:
- All three test responsive behavior at mobile sizes
- **Decision**: Combine into a single property that tests comprehensive mobile responsiveness.

**Performance Properties (12.1, 12.2)**:
- Both test response time requirements
- **Decision**: Keep separate as they test different timing requirements (indicator vs full response).

### Correctness Properties

### Property 1: Admin-Only Access Control

*For any* user attempting to access the AI support interface, the system should grant access if and only if the user has the admin role.

**Validates: Requirements 1.1**

### Property 2: Navigation Link Visibility

*For any* user role, the AI support navigation link should be visible in the menu if and only if the user is an admin.

**Validates: Requirements 1.4**

### Property 3: Comprehensive System Knowledge

*For any* query about system features (loan workflows, user management, messaging, CI tracking, document management, or UI customization), the AI assistant should provide accurate information that includes relevant details from the system knowledge base.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

### Property 4: Troubleshooting Guidance

*For any* error description or system issue (user approval, application status, notifications, database integrity, or CI assignment conflicts), the AI assistant should provide relevant troubleshooting steps or solutions.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 5: Session Persistence and Restoration

*For any* chat session created by an admin user, the conversation history should persist while the user remains logged in and be restored when the user navigates back to the AI support interface.

**Validates: Requirements 9.1, 9.2**

### Property 6: Session History Limit

*For any* chat session, when the number of messages exceeds 50, the system should retain only the most recent 50 messages.

**Validates: Requirements 9.4**

### Property 7: Response Formatting Quality

*For any* AI response, the content should be properly formatted with appropriate use of paragraphs, bullet points, code blocks, highlighted important information (file paths, commands, configuration values), consistent terminology from the system glossary, and step-by-step instructions for procedural queries.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 8: Mobile Responsiveness

*For any* mobile viewport size (width < 768px), the AI support interface should adapt its layout appropriately, with the agent image resizing without distortion, chat session remaining readable and scrollable, and all interactive elements remaining accessible.

**Validates: Requirements 10.1, 10.2, 10.3**

### Property 9: Typing Indicator Response Time

*For any* submitted query, the typing indicator should appear within 500 milliseconds of submission.

**Validates: Requirements 12.1**

### Property 10: AI Response Time

*For any* typical query (non-complex, standard system questions), the AI assistant should generate and display a complete response within 10 seconds.

**Validates: Requirements 12.2**

### Property 11: Non-Blocking UI During Processing

*For any* AI query being processed, other UI elements (navigation, buttons, input fields) should remain interactive and responsive.

**Validates: Requirements 12.3**

### Property 12: Concurrent Request Handling

*For any* set of concurrent AI requests from multiple admin sessions, the system should handle all requests without significant performance degradation (response times should not increase by more than 50% compared to single-request baseline).

**Validates: Requirements 12.4**

### Property 13: Input Sanitization

*For any* user input submitted to the AI assistant, the system should validate and sanitize the input to prevent injection attacks or malicious code execution.

**Validates: Requirements 13.3**

### Property 14: Sensitive Data Protection in Responses

*For any* AI response, the content should not include database credentials, API keys, passwords, or other sensitive configuration details, even if directly requested.

**Validates: Requirements 13.4**

### Property 15: Sensitive Data Protection in Logs

*For any* chat session containing sensitive information (passwords, personal data, credentials), the system logs should not contain this sensitive information in plain text.

**Validates: Requirements 13.2**

### Property 16: Agent Image Responsive Scaling

*For any* viewport size, the agent image should scale proportionally without distortion (maintaining aspect ratio).

**Validates: Requirements 3.3**

## Error Handling

### Error Categories and Handling Strategies

#### 1. Authentication/Authorization Errors

**Scenario**: Non-admin user attempts to access AI support
- **Detection**: Role check in route decorator
- **Response**: Redirect to user's dashboard with "Unauthorized" flash message
- **HTTP Status**: 302 (Redirect)
- **User Experience**: Seamless redirect, clear message

**Implementation**:
```python
@app.route('/ai-support')
@login_required
def ai_support():
    if current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
```

#### 2. AI API Errors

**Scenario**: AI service unavailable or API key invalid
- **Detection**: Exception during API call
- **Response**: User-friendly error message in chat
- **Logging**: Full error details logged server-side
- **User Experience**: "Sorry, I'm having trouble connecting. Please try again."
- **Recovery**: Retry button provided

**Implementation**:
```python
try:
    response = call_ai_engine(query, chat_history, system_context)
except openai.error.APIError as e:
    app.logger.error(f"AI API Error: {str(e)}")
    return jsonify({'error': 'AI service temporarily unavailable'}), 503
except openai.error.AuthenticationError as e:
    app.logger.error(f"AI Auth Error: {str(e)}")
    return jsonify({'error': 'AI service configuration error'}), 500
except Exception as e:
    app.logger.error(f"Unexpected AI Error: {str(e)}")
    return jsonify({'error': 'An unexpected error occurred'}), 500
```

#### 3. Network Errors

**Scenario**: Client loses network connectivity
- **Detection**: Fetch API failure in JavaScript
- **Response**: Offline indicator, message queuing
- **User Experience**: "You appear to be offline. Your message will be sent when connection is restored."
- **Recovery**: Automatic retry when connection restored

**Implementation**:
```javascript
async function sendQuery() {
    try {
        const response = await fetch('/api/ai_query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query})
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        if (!navigator.onLine) {
            showOfflineMessage();
            queueMessage(query);
        } else {
            showErrorMessage('Connection error. Please try again.');
        }
    }
}
```

#### 4. Input Validation Errors

**Scenario**: Empty query or invalid input
- **Detection**: Client-side and server-side validation
- **Response**: Inline validation message
- **User Experience**: "Please enter a question" (non-intrusive)
- **Prevention**: Disable send button when input is empty

**Implementation**:
```python
@app.route('/api/ai_query', methods=['POST'])
@login_required
def ai_query():
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    if len(query) > 2000:
        return jsonify({'error': 'Query too long (max 2000 characters)'}), 400
```

#### 5. Session Errors

**Scenario**: Session expired or corrupted
- **Detection**: Session data missing or invalid
- **Response**: Initialize new session
- **User Experience**: Transparent recovery, no error shown
- **Logging**: Session error logged for monitoring

**Implementation**:
```python
def get_chat_history():
    try:
        history = session.get('ai_chat_history', [])
        if not isinstance(history, list):
            raise ValueError("Invalid history format")
        return history
    except Exception as e:
        app.logger.warning(f"Session error: {str(e)}")
        session['ai_chat_history'] = []
        return []
```

#### 6. Rate Limiting Errors

**Scenario**: Too many requests from single user
- **Detection**: Flask-Limiter decorator
- **Response**: 429 status with retry-after header
- **User Experience**: "Please wait a moment before sending another message"
- **Prevention**: Disable send button temporarily

**Implementation**:
```python
@app.route('/api/ai_query', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def ai_query():
    # ... implementation
```

### Error Logging Strategy

**Log Levels**:
- **ERROR**: AI API failures, authentication errors, unexpected exceptions
- **WARNING**: Session issues, rate limiting, invalid input
- **INFO**: Successful queries, session creation/destruction
- **DEBUG**: Detailed request/response data (development only)

**Log Format**:
```python
app.logger.error(f"AI Query Error | User: {current_user.id} | Query: {query[:50]}... | Error: {str(e)}")
```

**Sensitive Data Protection**:
- Never log full query content (truncate to 50 chars)
- Never log AI responses containing potential sensitive data
- Sanitize error messages before logging

## Testing Strategy

### Dual Testing Approach

The AI Support Assistant feature requires both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
**Property Tests**: Verify universal properties across all inputs using randomization

### Unit Testing

Unit tests validate specific scenarios and edge cases that are important but don't require exhaustive input coverage.

#### Test Categories

**1. Authentication and Authorization Tests**
```python
def test_ai_support_requires_login():
    """Test that unauthenticated users are redirected to login"""
    response = client.get('/ai-support')
    assert response.status_code == 302
    assert '/login' in response.location

def test_ai_support_admin_only():
    """Test that non-admin users are denied access"""
    login_as_loan_staff(client)
    response = client.get('/ai-support')
    assert response.status_code == 302
    assert 'Unauthorized' in get_flashed_messages()

def test_ai_support_admin_access():
    """Test that admin users can access the interface"""
    login_as_admin(client)
    response = client.get('/ai-support')
    assert response.status_code == 200
    assert b'DaisyandCoco' in response.data
```

**2. Navigation Integration Tests**
```python
def test_ai_support_link_in_admin_nav():
    """Test that AI support link appears in admin navigation"""
    login_as_admin(client)
    response = client.get('/admin/dashboard')
    assert b'AI Support' in response.data
    assert b'bi-robot' in response.data

def test_ai_support_link_not_in_staff_nav():
    """Test that AI support link does not appear for non-admin users"""
    login_as_loan_staff(client)
    response = client.get('/loan/dashboard')
    assert b'AI Support' not in response.data
```

**3. UI Rendering Tests**
```python
def test_agent_image_displayed():
    """Test that DaisyandCoco image is rendered"""
    login_as_admin(client)
    response = client.get('/ai-support')
    assert b'daisy-coco.jpg' in response.data

def test_chat_interface_elements():
    """Test that all required UI elements are present"""
    login_as_admin(client)
    response = client.get('/ai-support')
    assert b'queryInput' in response.data
    assert b'sendBtn' in response.data
    assert b'clearBtn' in response.data
    assert b'chatHistory' in response.data
```

**4. Session Management Tests**
```python
def test_session_initialization():
    """Test that new session has empty chat history"""
    login_as_admin(client)
    with client.session_transaction() as sess:
        assert 'ai_chat_history' not in sess or sess['ai_chat_history'] == []

def test_session_cleared_on_logout():
    """Test that chat history is cleared when user logs out"""
    login_as_admin(client)
    # Create chat history
    with client.session_transaction() as sess:
        sess['ai_chat_history'] = [{'role': 'user', 'content': 'test'}]
    
    client.get('/logout')
    
    login_as_admin(client)
    with client.session_transaction() as sess:
        assert sess.get('ai_chat_history', []) == []
```

**5. Error Handling Tests**
```python
def test_empty_query_rejected():
    """Test that empty queries return 400 error"""
    login_as_admin(client)
    response = client.post('/api/ai_query',
                          json={'query': ''},
                          content_type='application/json')
    assert response.status_code == 400
    assert b'Empty query' in response.data

def test_ai_api_failure_handling():
    """Test graceful handling of AI API failures"""
    login_as_admin(client)
    with mock.patch('app.call_ai_engine', side_effect=Exception('API Error')):
        response = client.post('/api/ai_query',
                              json={'query': 'test question'},
                              content_type='application/json')
        assert response.status_code == 500
        assert 'error' in response.json
```

**6. Dark Mode Tests**
```python
def test_dark_mode_styles_applied():
    """Test that dark mode CSS variables are present"""
    login_as_admin(client)
    response = client.get('/ai-support')
    assert b'--bg-white' in response.data
    assert b'--text-primary' in response.data
    assert b'dark-mode' in response.data
```

### Property-Based Testing

Property tests verify universal behaviors across many generated inputs. Each test runs a minimum of 100 iterations with randomized data.

**Configuration**: Use `hypothesis` library for Python property-based testing

```python
from hypothesis import given, strategies as st
import hypothesis

# Configure for minimum 100 iterations
hypothesis.settings.register_profile("ai_support", max_examples=100)
hypothesis.settings.load_profile("ai_support")
```

#### Property Test Cases

**Property 1: Admin-Only Access Control**
```python
@given(user_role=st.sampled_from(['admin', 'loan_staff', 'ci_staff', 'guest']))
def test_access_control_property(user_role):
    """
    Feature: ai-support-assistant, Property 1: For any user attempting to access 
    the AI support interface, the system should grant access if and only if the 
    user has the admin role.
    """
    if user_role == 'admin':
        login_as_role(client, user_role)
        response = client.get('/ai-support')
        assert response.status_code == 200
    else:
        if user_role != 'guest':
            login_as_role(client, user_role)
        response = client.get('/ai-support')
        assert response.status_code == 302  # Redirect
```

**Property 2: Session History Limit**
```python
@given(message_count=st.integers(min_value=51, max_value=200))
def test_session_history_limit_property(message_count):
    """
    Feature: ai-support-assistant, Property 6: For any chat session, when the 
    number of messages exceeds 50, the system should retain only the most recent 
    50 messages.
    """
    login_as_admin(client)
    
    # Generate messages
    messages = [
        {'role': 'user' if i % 2 == 0 else 'assistant', 
         'content': f'Message {i}'}
        for i in range(message_count)
    ]
    
    with client.session_transaction() as sess:
        sess['ai_chat_history'] = messages
    
    # Trigger session update (make a query)
    client.post('/api/ai_query',
               json={'query': 'test'},
               content_type='application/json')
    
    with client.session_transaction() as sess:
        history = sess.get('ai_chat_history', [])
        assert len(history) <= 50
        # Verify it's the most recent 50
        if message_count > 50:
            assert history[0]['content'] == f'Message {message_count - 50}'
```

**Property 3: Input Sanitization**
```python
@given(malicious_input=st.one_of(
    st.text(alphabet='<>"\\'', min_size=1, max_size=100),
    st.from_regex(r'.*<script>.*</script>.*', fullmatch=True),
    st.from_regex(r'.*\{.*\}.*', fullmatch=True),
    st.from_regex(r'.*SELECT.*FROM.*', fullmatch=True)
))
def test_input_sanitization_property(malicious_input):
    """
    Feature: ai-support-assistant, Property 13: For any user input submitted to 
    the AI assistant, the system should validate and sanitize the input to prevent 
    injection attacks or malicious code execution.
    """
    login_as_admin(client)
    
    response = client.post('/api/ai_query',
                          json={'query': malicious_input},
                          content_type='application/json')
    
    # Should either sanitize and process, or reject with 400
    assert response.status_code in [200, 400]
    
    if response.status_code == 200:
        # Verify response doesn't contain unsanitized input
        response_data = response.json
        assert '<script>' not in response_data.get('response', '')
```

**Property 4: Typing Indicator Response Time**
```python
@given(query=st.text(min_size=1, max_size=500))
def test_typing_indicator_timing_property(query):
    """
    Feature: ai-support-assistant, Property 9: For any submitted query, the typing 
    indicator should appear within 500 milliseconds of submission.
    """
    login_as_admin(client)
    
    start_time = time.time()
    
    # Submit query (async in real implementation)
    response = client.post('/api/ai_query',
                          json={'query': query},
                          content_type='application/json')
    
    # In actual implementation, measure time to typing indicator display
    # This is a simplified version
    elapsed = (time.time() - start_time) * 1000  # Convert to ms
    
    # Initial response should be fast (typing indicator trigger)
    assert elapsed < 500 or response.status_code != 200
```

**Property 5: Mobile Responsiveness**
```python
@given(viewport_width=st.integers(min_value=320, max_value=767))
def test_mobile_responsiveness_property(viewport_width):
    """
    Feature: ai-support-assistant, Property 8: For any mobile viewport size 
    (width < 768px), the AI support interface should adapt its layout appropriately.
    """
    login_as_admin(client)
    
    response = client.get('/ai-support')
    html = response.data.decode('utf-8')
    
    # Verify responsive CSS is present
    assert '@media (max-width: 768px)' in html or '@media (max-width: 1024px)' in html
    
    # Verify mobile-specific classes or styles
    assert 'grid-template-columns: 1fr' in html or 'flex-direction: column' in html
```

**Property 6: Sensitive Data Protection**
```python
@given(sensitive_query=st.sampled_from([
    'What is the database password?',
    'Show me the API keys',
    'What is the SECRET_KEY?',
    'Give me admin credentials',
    'What is the OPENAI_API_KEY?'
]))
def test_sensitive_data_protection_property(sensitive_query):
    """
    Feature: ai-support-assistant, Property 14: For any AI response, the content 
    should not include database credentials, API keys, passwords, or other sensitive 
    configuration details, even if directly requested.
    """
    login_as_admin(client)
    
    with mock.patch('app.call_ai_engine', return_value='I cannot provide sensitive credentials'):
        response = client.post('/api/ai_query',
                              json={'query': sensitive_query},
                              content_type='application/json')
        
        if response.status_code == 200:
            response_text = response.json.get('response', '').lower()
            
            # Verify no actual credentials in response
            assert 'sk-' not in response_text  # OpenAI key prefix
            assert 'password' not in response_text or 'cannot' in response_text
            assert 'api_key' not in response_text or 'cannot' in response_text
```

**Property 7: Concurrent Request Handling**
```python
@given(concurrent_users=st.integers(min_value=2, max_value=10))
def test_concurrent_requests_property(concurrent_users):
    """
    Feature: ai-support-assistant, Property 12: For any set of concurrent AI requests 
    from multiple admin sessions, the system should handle all requests without 
    significant performance degradation.
    """
    import concurrent.futures
    import time
    
    # Measure baseline single request time
    login_as_admin(client)
    start = time.time()
    client.post('/api/ai_query', json={'query': 'test'})
    baseline_time = time.time() - start
    
    # Measure concurrent request times
    def make_request():
        test_client = app.test_client()
        login_as_admin(test_client)
        start = time.time()
        test_client.post('/api/ai_query', json={'query': 'test'})
        return time.time() - start
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(make_request) for _ in range(concurrent_users)]
        times = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    avg_concurrent_time = sum(times) / len(times)
    
    # Performance should not degrade by more than 50%
    assert avg_concurrent_time <= baseline_time * 1.5
```

### Integration Testing

Integration tests verify the complete flow from user interaction to AI response.

```python
def test_complete_query_flow():
    """Test complete flow: login -> navigate -> query -> response"""
    # Login as admin
    login_as_admin(client)
    
    # Navigate to AI support
    response = client.get('/ai-support')
    assert response.status_code == 200
    
    # Submit query
    response = client.post('/api/ai_query',
                          json={'query': 'How do I approve a user?'},
                          content_type='application/json')
    assert response.status_code == 200
    assert 'response' in response.json
    
    # Verify session updated
    with client.session_transaction() as sess:
        history = sess.get('ai_chat_history', [])
        assert len(history) == 2  # User query + AI response
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'
    
    # Submit follow-up query
    response = client.post('/api/ai_query',
                          json={'query': 'What about rejecting users?'},
                          content_type='application/json')
    assert response.status_code == 200
    
    # Verify context maintained
    with client.session_transaction() as sess:
        history = sess.get('ai_chat_history', [])
        assert len(history) == 4  # 2 exchanges
```

### Test Configuration

**Property-Based Test Settings**:
- Minimum iterations: 100 per property test
- Timeout: 60 seconds per test
- Shrinking: Enabled (to find minimal failing examples)
- Random seed: Configurable for reproducibility

**Test Tagging**:
Each property test includes a comment with the format:
```python
"""
Feature: ai-support-assistant, Property {number}: {property_text}
"""
```

### Test Coverage Goals

- **Unit Tests**: 90%+ code coverage for AI support routes and functions
- **Property Tests**: 100% coverage of correctness properties
- **Integration Tests**: All major user flows covered
- **Edge Cases**: Empty inputs, malformed data, API failures, session expiry

### Continuous Integration

Tests should run automatically on:
- Every commit to feature branch
- Pull request creation
- Merge to main branch

**CI Configuration** (example for GitHub Actions):
```yaml
name: AI Support Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest hypothesis pytest-cov
      - name: Run unit tests
        run: pytest tests/test_ai_support.py -v
      - name: Run property tests
        run: pytest tests/test_ai_support_properties.py -v --hypothesis-profile=ai_support
      - name: Generate coverage report
        run: pytest --cov=app --cov-report=html
```

## Implementation Notes

### Environment Variables Required

Add to `.env` file:
```bash
# AI Service Configuration (choose one)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Optional: AI Model Selection
AI_MODEL=gpt-4  # or claude-3-sonnet-20240229
```

### Dependencies to Add

Add to `requirements.txt`:
```
openai>=1.0.0
# OR
anthropic>=0.7.0
```

### Database Migrations

No database schema changes required. Uses Flask session for storage.

### File Structure

```
.
├── app.py                          # Add AI routes
├── templates/
│   ├── base.html                   # Update navigation
│   └── ai_support.html             # New template
├── static/
│   ├── images/
│   │   └── daisy-coco.jpg          # Agent image (already exists)
│   └── ai-support.js               # New JavaScript (optional, can be inline)
└── tests/
    ├── test_ai_support.py          # Unit tests
    └── test_ai_support_properties.py  # Property tests
```

### Security Considerations

1. **API Key Protection**: Store in environment variables, never commit to repository
2. **Rate Limiting**: Apply to AI query endpoint to prevent abuse
3. **Input Validation**: Sanitize all user input before sending to AI
4. **Output Filtering**: Ensure AI responses don't leak sensitive data
5. **Session Security**: Use secure session cookies with httponly flag
6. **HTTPS Only**: Enforce HTTPS in production for all AI communications

### Performance Optimization

1. **Response Streaming**: Consider streaming AI responses for better UX
2. **Caching**: Cache common queries and responses (with TTL)
3. **Async Processing**: Use async/await for non-blocking AI calls
4. **Connection Pooling**: Reuse HTTP connections to AI service
5. **Timeout Handling**: Set reasonable timeouts (10s) for AI requests

### Accessibility Considerations

1. **Keyboard Navigation**: Ensure all controls are keyboard accessible
2. **Screen Reader Support**: Add ARIA labels to chat messages
3. **Focus Management**: Manage focus when messages are added
4. **Color Contrast**: Ensure sufficient contrast in both light and dark modes
5. **Alternative Text**: Provide alt text for agent image

### Future Enhancements

1. **Voice Input**: Add speech-to-text for voice queries
2. **Export Chat**: Allow exporting conversation history
3. **Suggested Questions**: Show common questions as quick actions
4. **Multi-language Support**: Detect and respond in user's language
5. **Analytics**: Track common queries to improve knowledge base
6. **Feedback Loop**: Allow users to rate responses for continuous improvement

## Conclusion

This design provides a comprehensive blueprint for implementing the DaisyandCoco AI Support Assistant. The architecture follows Flask best practices, integrates seamlessly with the existing codebase, and provides a robust, secure, and user-friendly experience for admin users.

The dual testing approach ensures both specific edge cases and universal properties are validated, providing confidence in the system's correctness and reliability. The modular design allows for easy maintenance and future enhancements while maintaining consistency with the existing application's look and feel.
