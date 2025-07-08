import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from procur.core.config import get_settings
from procur.models.schemas import EmailTemplate
import logging
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self._email_queue = []
        self._stats = {
            "sent": 0,
            "failed": 0,
            "queued": 0
        }
    
    def _send_email_sync(self, to_email: str, template: EmailTemplate) -> Dict[str, Any]:
        """Send email synchronously with detailed result"""
        start_time = time.time()
        result = {
            "email": to_email,
            "success": False,
            "error": None,
            "sent_at": None,
            "duration": 0
        }
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.settings.SMTP_FROM_EMAIL
            msg['To'] = to_email
            msg['Subject'] = template.subject
            
            # Add text and HTML parts
            text_part = MIMEText(template.text_body, 'plain', 'utf-8')
            html_part = MIMEText(template.html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.settings.SMTP_SERVER, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            result.update({
                "success": True,
                "sent_at": time.time(),
                "duration": time.time() - start_time
            })
            
            self._stats["sent"] += 1
            logger.info(f"Email sent successfully to {to_email} in {result['duration']:.2f}s")
            
        except smtplib.SMTPAuthenticationError as e:
            result["error"] = f"SMTP Authentication failed: {str(e)}"
            logger.error(f"SMTP auth error sending to {to_email}: {e}")
            self._stats["failed"] += 1
            
        except smtplib.SMTPRecipientsRefused as e:
            result["error"] = f"Recipient refused: {str(e)}"
            logger.error(f"Recipient refused {to_email}: {e}")
            self._stats["failed"] += 1
            
        except smtplib.SMTPException as e:
            result["error"] = f"SMTP error: {str(e)}"
            logger.error(f"SMTP error sending to {to_email}: {e}")
            self._stats["failed"] += 1
            
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            self._stats["failed"] += 1
        
        result["duration"] = time.time() - start_time
        return result
    
    async def send_email(self, to_email: str, template: EmailTemplate) -> Dict[str, Any]:
        """Send single email asynchronously with result tracking"""
        if not self.settings.ENABLE_EMAIL_NOTIFICATIONS:
            logger.info(f"Email notifications disabled, skipping email to {to_email}")
            return {
                "email": to_email,
                "success": True,
                "skipped": True,
                "reason": "notifications_disabled"
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._send_email_sync,
            to_email,
            template
        )
        
        return result
    
    async def send_bulk_emails(self, email_list: List[str], template: EmailTemplate) -> List[Dict[str, Any]]:
        """Send emails to multiple recipients with batch processing"""
        if not self.settings.ENABLE_EMAIL_NOTIFICATIONS:
            logger.info(f"Email notifications disabled, skipping {len(email_list)} emails")
            return [
                {
                    "email": email,
                    "success": True,
                    "skipped": True,
                    "reason": "notifications_disabled"
                }
                for email in email_list
            ]
        
        # Process emails in batches of 10 to avoid overwhelming SMTP server
        batch_size = 10
        all_results = []
        
        for i in range(0, len(email_list), batch_size):
            batch = email_list[i:i + batch_size]
            logger.info(f"Processing email batch {i//batch_size + 1}/{(len(email_list) + batch_size - 1)//batch_size}")
            
            # Send batch asynchronously
            tasks = [self.send_email(email, template) for email in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            processed_results = []
            for result in batch_results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "email": "unknown",
                        "success": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            all_results.extend(processed_results)
            
            # Small delay between batches to be respectful to SMTP server
            if i + batch_size < len(email_list):
                await asyncio.sleep(1)
        
        # Log summary
        successful = len([r for r in all_results if r.get("success")])
        failed = len([r for r in all_results if not r.get("success")])
        logger.info(f"Bulk email completed: {successful} sent, {failed} failed")
        
        return all_results
    
    async def send_templated_email(
        self, 
        to_email: str, 
        template_name: str, 
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email using predefined template with data substitution"""
        try:
            # Import here to avoid circular imports
            from procur.templates.email_templates import get_template_by_name
            
            template = get_template_by_name(template_name, template_data)
            return await self.send_email(to_email, template)
            
        except Exception as e:
            logger.error(f"Failed to send templated email '{template_name}' to {to_email}: {e}")
            return {
                "email": to_email,
                "success": False,
                "error": f"Template error: {str(e)}"
            }
    
    def get_stats(self) -> Dict[str, int]:
        """Get email service statistics for React dashboard"""
        return self._stats.copy()
    
    def reset_stats(self):
        """Reset email statistics"""
        self._stats = {
            "sent": 0,
            "failed": 0,
            "queued": 0
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection for React settings page"""
        try:
            with smtplib.SMTP(self.settings.SMTP_SERVER, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
            
            return {
                "success": True,
                "message": "SMTP connection successful",
                "server": self.settings.SMTP_SERVER,
                "port": self.settings.SMTP_PORT
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"SMTP connection failed: {str(e)}",
                "server": self.settings.SMTP_SERVER,
                "port": self.settings.SMTP_PORT,
                "error": str(e)
            }
    
    async def queue_email(self, to_email: str, template: EmailTemplate, priority: int = 0):
        """Queue email for later sending (useful for high-volume scenarios)"""
        email_item = {
            "to_email": to_email,
            "template": template,
            "priority": priority,
            "queued_at": time.time()
        }
        
        self._email_queue.append(email_item)
        self._stats["queued"] += 1
        
        # Sort queue by priority (higher priority first)
        self._email_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(f"Email queued for {to_email}, queue size: {len(self._email_queue)}")
    
    async def process_queue(self, batch_size: int = 10) -> Dict[str, Any]:
        """Process queued emails in batches"""
        if not self._email_queue:
            return {
                "processed": 0,
                "remaining": 0,
                "results": []
            }
        
        # Get batch from queue
        batch = self._email_queue[:batch_size]
        self._email_queue = self._email_queue[batch_size:]
        
        # Send batch
        results = []
        for item in batch:
            result = await self.send_email(item["to_email"], item["template"])
            result["priority"] = item["priority"]
            result["queue_time"] = time.time() - item["queued_at"]
            results.append(result)
            self._stats["queued"] -= 1
        
        return {
            "processed": len(batch),
            "remaining": len(self._email_queue),
            "results": results
        }

# Global email service instance
email_service = EmailService()

# EOF