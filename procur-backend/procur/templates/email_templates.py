from procur.models.schemas import EmailTemplate
from typing import Dict, Any

def get_base_html_template() -> str:
    """Base HTML template with consistent styling for all emails"""
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6; 
                color: #374151; 
                margin: 0; 
                padding: 0; 
                background-color: #f9fafb;
            }}
            .email-container {{ 
                max-width: 600px; 
                margin: 20px auto; 
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                overflow: hidden;
            }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 40px 30px; 
                text-align: center; 
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 700;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 16px;
            }}
            .content {{ 
                padding: 40px 30px; 
            }}
            .content p {{
                margin: 0 0 16px 0;
                font-size: 16px;
                line-height: 1.6;
            }}
            .button {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 16px 32px; 
                text-decoration: none; 
                border-radius: 8px; 
                display: inline-block; 
                font-weight: 600;
                font-size: 16px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                transition: transform 0.2s ease;
            }}
            .button:hover {{
                transform: translateY(-1px);
            }}
            .info-box {{ 
                background: #f8fafc; 
                border: 1px solid #e2e8f0;
                padding: 24px; 
                margin: 24px 0; 
                border-radius: 8px; 
                border-left: 4px solid #667eea;
            }}
            .info-box h3 {{
                color: #475569; 
                margin: 0 0 12px 0;
                font-size: 18px;
            }}
            .info-box ul {{
                color: #64748b; 
                padding-left: 20px;
                margin: 0;
            }}
            .info-box ul li {{
                margin-bottom: 8px;
            }}
            .footer {{ 
                background: #f8fafc;
                padding: 30px; 
                text-align: center; 
                color: #64748b; 
                font-size: 14px;
                border-top: 1px solid #e2e8f0;
            }}
            .footer p {{
                margin: 5px 0;
                font-size: 14px;
            }}
            .highlight {{
                color: #667eea;
                font-weight: 600;
            }}
            .center {{
                text-align: center;
                margin: 30px 0;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            {content}
        </div>
    </body>
    </html>
    """

def get_join_request_template(group_name: str, requester_name: str, requester_email: str, message: str, request_id: str) -> EmailTemplate:
    """Email template for join request notifications"""
    
    subject = f"New join request for {group_name}"
    
    content = f"""
        <div class="header">
            <h1>🔔 New Join Request</h1>
            <p>Someone wants to join {group_name}</p>
        </div>
        <div class="content">
            <p><strong>Hi there!</strong></p>
            <p>You have a new join request for your group <span class="highlight">{group_name}</span>.</p>
            
            <div class="info-box">
                <h3>Request Details</h3>
                <p><strong>Requester:</strong> {requester_name}</p>
                <p><strong>Email:</strong> {requester_email}</p>
                <p><strong>Message:</strong> {message or 'No message provided'}</p>
            </div>
            
            <p>Please review this request and decide whether to approve or decline it. You can manage all join requests from your group dashboard.</p>
            
            <div class="center">
                <a href="#" class="button">Review Request</a>
            </div>
        </div>
        <div class="footer">
            <p>This is an automated message from Procur</p>
            <p>You're receiving this because you're an admin of {group_name}</p>
        </div>
    """
    
    html_body = get_base_html_template().format(content=content)
    
    text_body = f"""
    New Join Request for {group_name}
    
    Hi there!
    
    You have a new join request for your group {group_name}.
    
    Request Details:
    - Requester: {requester_name}
    - Email: {requester_email}
    - Message: {message or 'No message provided'}
    
    Please review this request in your Procur dashboard and decide whether to approve or decline it.
    
    This is an automated message from Procur
    You're receiving this because you're an admin of {group_name}
    """
    
    return EmailTemplate(
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

def get_join_approved_template(group_name: str, user_name: str) -> EmailTemplate:
    """Email template for join approval notifications"""
    
    subject = f"Welcome to {group_name}! 🎉"
    
    content = f"""
        <div class="header">
            <h1>🎉 Welcome aboard!</h1>
            <p>You've been approved to join {group_name}</p>
        </div>
        <div class="content">
            <p><strong>Hi {user_name}!</strong></p>
            <p>Great news! Your request to join <span class="highlight">{group_name}</span> has been approved.</p>
            
            <div class="info-box">
                <h3>What's next?</h3>
                <ul>
                    <li>Explore the group's current purchasing campaigns</li>
                    <li>Connect with other members in your industry</li>
                    <li>Start saving with group purchasing power</li>
                    <li>Participate in group discussions and planning</li>
                </ul>
            </div>
            
            <p>You can now access all group features and start benefiting from collective purchasing power. Welcome to the community!</p>
            
            <div class="center">
                <a href="#" class="button">Visit Your Group</a>
            </div>
        </div>
        <div class="footer">
            <p>This is an automated message from Procur</p>
            <p>Happy purchasing! 🛒</p>
        </div>
    """
    
    html_body = get_base_html_template().format(content=content)
    
    text_body = f"""
    Welcome to {group_name}!
    
    Hi {user_name}!
    
    Great news! Your request to join {group_name} has been approved.
    
    What's next?
    • Explore the group's current purchasing campaigns
    • Connect with other members in your industry
    • Start saving with group purchasing power
    • Participate in group discussions and planning
    
    You can now access all group features and start benefiting from collective purchasing power. Welcome to the community!
    
    Visit your Procur dashboard to get started.
    
    This is an automated message from Procur
    Happy purchasing!
    """
    
    return EmailTemplate(
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

def get_welcome_template(user_name: str) -> EmailTemplate:
    """Welcome email template for new users"""
    
    subject = "Welcome to Procur! 🚀"
    
    content = f"""
        <div class="header">
            <h1>🚀 Welcome to Procur!</h1>
            <p>Your journey to smarter purchasing starts here</p>
        </div>
        <div class="content">
            <p><strong>Hi {user_name}!</strong></p>
            <p>Welcome to Procur! You've just joined a community that's revolutionizing how businesses approach purchasing through the power of group buying.</p>
            
            <div class="info-box">
                <h3>What you can do with Procur:</h3>
                <ul>
                    <li><strong>Join buying groups</strong> in your industry for better pricing</li>
                    <li><strong>Create your own groups</strong> and invite other businesses</li>
                    <li><strong>Access exclusive discounts</strong> from verified suppliers</li>
                    <li><strong>Streamline procurement</strong> with our integrated platform</li>
                    <li><strong>Network with peers</strong> in your industry</li>
                </ul>
            </div>
            
            <p>Ready to get started? Here are your next steps:</p>
            <p>1. <strong>Complete your profile</strong> to help others find you<br>
            2. <strong>Browse groups</strong> in your industry<br>
            3. <strong>Join your first buying group</strong><br>
            4. <strong>Start saving</strong> with group purchasing power</p>
            
            <div class="center">
                <a href="#" class="button">Complete Your Profile</a>
            </div>
            
            <p>If you have any questions, our support team is here to help. We're excited to have you aboard!</p>
        </div>
        <div class="footer">
            <p>This is an automated welcome message from Procur</p>
            <p>Questions? Reply to this email or contact our support team</p>
        </div>
    """
    
    html_body = get_base_html_template().format(content=content)
    
    text_body = f"""
    Welcome to Procur!
    
    Hi {user_name}!
    
    Welcome to Procur! You've just joined a community that's revolutionizing how businesses approach purchasing through the power of group buying.
    
    What you can do with Procur:
    • Join buying groups in your industry for better pricing
    • Create your own groups and invite other businesses
    • Access exclusive discounts from verified suppliers
    • Streamline procurement with our integrated platform
    • Network with peers in your industry
    
    Ready to get started? Here are your next steps:
    1. Complete your profile to help others find you
    2. Browse groups in your industry
    3. Join your first buying group
    4. Start saving with group purchasing power
    
    If you have any questions, our support team is here to help. We're excited to have you aboard!
    
    This is an automated welcome message from Procur
    Questions? Reply to this email or contact our support team
    """
    
    return EmailTemplate(
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

def get_invitation_template(group_name: str, inviter_name: str, invitation_url: str, group_description: str = "") -> EmailTemplate:
    """Enhanced invitation email template"""
    
    subject = f"Join {group_name} on Procur - Invitation from {inviter_name}"
    
    content = f"""
        <div class="header">
            <h1>🎉 You're Invited!</h1>
            <p>Join {group_name} on Procur</p>
        </div>
        <div class="content">
            <p><strong>Hi there!</strong></p>
            <p><span class="highlight">{inviter_name}</span> has invited you to join <span class="highlight">{group_name}</span> on Procur.</p>
            
            {f'<p><em>"{group_description}"</em></p>' if group_description else ''}
            
            <div class="info-box">
                <h3>Why join this group?</h3>
                <ul>
                    <li><strong>Better pricing:</strong> Access exclusive group discounts from verified suppliers</li>
                    <li><strong>Industry connections:</strong> Network with other businesses in your field</li>
                    <li><strong>Streamlined purchasing:</strong> Simplified procurement process</li>
                    <li><strong>Transparent pricing:</strong> See exactly what you're paying and why</li>
                    <li><strong>Bulk buying power:</strong> Leverage collective volume for better deals</li>
                </ul>
            </div>
            
            <p>Procur helps businesses like yours save money and time through the power of group purchasing. Join thousands of companies already benefiting from our platform.</p>
            
            <div class="center">
                <a href="{invitation_url}" class="button">Join {group_name}</a>
            </div>
            
            <p><strong>New to Procur?</strong> No problem! You'll be able to create your account as part of the joining process. It only takes a minute.</p>
            
            <p style="font-size: 14px; color: #64748b; margin-top: 30px;">
                <strong>Note:</strong> This invitation link will expire in 7 days. 
                Don't worry - if you miss it, you can always request to join the group directly.
            </p>
        </div>
        <div class="footer">
            <p>This invitation was sent by {inviter_name} via Procur</p>
            <p>Questions about Procur? <a href="#" style="color: #667eea;">Contact our support team</a></p>
        </div>
    """
    
    html_body = get_base_html_template().format(content=content)
    
    text_body = f"""
    You're Invited to Join {group_name} on Procur!
    
    Hi there!
    
    {inviter_name} has invited you to join {group_name} on Procur.
    
    {f'"{group_description}"' if group_description else ''}
    
    Why join this group?
    • Better pricing: Access exclusive group discounts from verified suppliers
    • Industry connections: Network with other businesses in your field
    • Streamlined purchasing: Simplified procurement process
    • Transparent pricing: See exactly what you're paying and why
    • Bulk buying power: Leverage collective volume for better deals
    
    Procur helps businesses like yours save money and time through the power of group purchasing. Join thousands of companies already benefiting from our platform.
    
    Join now: {invitation_url}
    
    New to Procur? No problem! You'll be able to create your account as part of the joining process. It only takes a minute.
    
    Note: This invitation link will expire in 7 days. Don't worry - if you miss it, you can always request to join the group directly.
    
    This invitation was sent by {inviter_name} via Procur
    Questions about Procur? Contact our support team
    """
   
    return EmailTemplate(
       subject=subject,
       html_body=html_body,
       text_body=text_body
   )

def get_password_reset_template(user_name: str, reset_url: str) -> EmailTemplate:
    """Password reset email template"""
   
    subject = "Reset your Procur password"
   
    content = f"""
       <div class="header">
           <h1>🔒 Password Reset</h1>
           <p>Reset your Procur account password</p>
       </div>
       <div class="content">
           <p><strong>Hi {user_name}!</strong></p>
           <p>We received a request to reset the password for your Procur account.</p>
           
           <div class="center">
               <a href="{reset_url}" class="button">Reset Password</a>
           </div>
           
           <p>This link will expire in 1 hour for security reasons.</p>
           
           <p><strong>Didn't request this?</strong> You can safely ignore this email. Your password won't be changed unless you click the link above.</p>
           
           <p>For security, this reset link will only work once. If you need to reset your password again, you'll need to request a new link.</p>
       </div>
       <div class="footer">
           <p>This is an automated security message from Procur</p>
           <p>Never share your password or reset links with anyone</p>
       </div>
    """
   
    html_body = get_base_html_template().format(content=content)
   
    text_body = f"""
    Reset your Procur password
   
    Hi {user_name}!
   
    We received a request to reset the password for your Procur account.
   
    Reset your password: {reset_url}
   
    This link will expire in 1 hour for security reasons.
   
    Didn't request this? You can safely ignore this email. Your password won't be changed unless you click the link above.
   
    For security, this reset link will only work once. If you need to reset your password again, you'll need to request a new link.
   
    This is an automated security message from Procur
    Never share your password or reset links with anyone
    """
   
    return EmailTemplate(
       subject=subject,
       html_body=html_body,
       text_body=text_body
    )

def get_template_by_name(template_name: str, data: Dict[str, Any]) -> EmailTemplate:
    """Get email template by name with data substitution"""
   
    template_functions = {
        "welcome": lambda d: get_welcome_template(d["user_name"]),
        "join_request": lambda d: get_join_request_template(
           d["group_name"], d["requester_name"], d["requester_email"], 
           d.get("message", ""), d["request_id"]
        ),
        "join_approved": lambda d: get_join_approved_template(d["group_name"], d["user_name"]),
        "invitation": lambda d: get_invitation_template(
           d["group_name"], d["inviter_name"], d["invitation_url"], 
           d.get("group_description", "")
        ),
        "password_reset": lambda d: get_password_reset_template(d["user_name"], d["reset_url"])
    }
   
    if template_name not in template_functions:
       raise ValueError(f"Unknown template: {template_name}")
   
    return template_functions[template_name](data)

# EOF