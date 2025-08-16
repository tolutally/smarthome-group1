"""
Notification Service for Smart Home System
Handles multiple notification channels: Email, SMS, Push, WebSocket, Webhooks
"""
import smtplib
import json
import logging
import requests
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask_socketio import emit
import vonage


class NotificationService:
    """Comprehensive notification service supporting multiple channels"""
    
    def __init__(self, socketio=None):
        """Initialize notification service with configuration"""
        self.socketio = socketio
        self.logger = logging.getLogger(__name__)
        
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_from = os.getenv('EMAIL_FROM', self.email_user)
        
        # SMS configuration (Vonage/Nexmo)
        self.vonage_api_key = os.getenv('VONAGE_API_KEY')
        self.vonage_api_secret = os.getenv('VONAGE_API_SECRET')
        self.sms_from = os.getenv('SMS_FROM', 'SmartHome')
        
        # Push notification configuration
        self.fcm_server_key = os.getenv('FCM_SERVER_KEY')
        self.fcm_url = 'https://fcm.googleapis.com/fcm/send'
        
        # Webhook configuration
        self.webhook_urls = self._load_webhook_urls()
        
        # Initialize external clients
        self._init_sms_client()
        
        self.logger.info("NotificationService initialized")
    
    def _init_sms_client(self):
        """Initialize SMS client"""
        if self.vonage_api_key and self.vonage_api_secret:
            self.sms_client = vonage.Client(
                key=self.vonage_api_key,
                secret=self.vonage_api_secret
            )
        else:
            self.sms_client = None
            self.logger.warning("SMS client not configured - missing Vonage credentials")
    
    def _load_webhook_urls(self) -> List[str]:
        """Load webhook URLs from environment"""
        webhook_env = os.getenv('WEBHOOK_URLS', '')
        if webhook_env:
            return [url.strip() for url in webhook_env.split(',') if url.strip()]
        return []
    
    def send_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main notification sending function
        
        Args:
            notification_data: {
                'type': 'alert|info|warning',
                'priority': 'low|medium|high|critical',
                'subject': 'Notification subject',
                'message': 'Notification message',
                'recipients': ['email@domain.com', '+1234567890'],
                'channels': ['email', 'sms', 'push', 'websocket', 'webhook'],
                'data': {...},  # Additional context data
                'template': 'alert_template'  # Optional email template
            }
        
        Returns:
            Dict with delivery status for each channel
        """
        self.logger.info(f"Sending notification: {notification_data.get('type', 'unknown')}")
        
        results = {
            'notification_id': f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'channels': {},
            'success': True
        }
        
        channels = notification_data.get('channels', ['websocket'])
        
        # Send via each requested channel
        for channel in channels:
            try:
                if channel == 'email':
                    result = self._send_email(notification_data)
                elif channel == 'sms':
                    result = self._send_sms(notification_data)
                elif channel == 'push':
                    result = self._send_push(notification_data)
                elif channel == 'websocket':
                    result = self._send_websocket(notification_data)
                elif channel == 'webhook':
                    result = self._send_webhook(notification_data)
                else:
                    result = {'success': False, 'error': f'Unknown channel: {channel}'}
                
                results['channels'][channel] = result
                
                if not result.get('success', False):
                    results['success'] = False
                    
            except Exception as e:
                self.logger.error(f"Failed to send via {channel}: {str(e)}")
                results['channels'][channel] = {
                    'success': False,
                    'error': str(e)
                }
                results['success'] = False
        
        self.logger.info(f"Notification sent - Success: {results['success']}")
        return results
    
    def _send_email(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email notification"""
        if not self.email_user or not self.email_password:
            return {'success': False, 'error': 'Email credentials not configured'}
        
        try:
            recipients = self._get_email_recipients(notification_data.get('recipients', []))
            if not recipients:
                return {'success': False, 'error': 'No email recipients found'}
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification_data.get('subject', 'Smart Home Notification')
            msg['From'] = self.email_from
            msg['To'] = ', '.join(recipients)
            
            # Create email content
            html_content = self._create_email_html(notification_data)
            text_content = notification_data.get('message', '')
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            return {
                'success': True,
                'recipients': recipients,
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Email sending failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_sms(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS notification"""
        if not self.sms_client:
            return {'success': False, 'error': 'SMS client not configured'}
        
        try:
            phone_numbers = self._get_phone_recipients(notification_data.get('recipients', []))
            if not phone_numbers:
                return {'success': False, 'error': 'No phone recipients found'}
            
            message = self._create_sms_message(notification_data)
            results = []
            
            for phone in phone_numbers:
                try:
                    sms = vonage.Sms(self.sms_client)
                    response = sms.send_message({
                        'from': self.sms_from,
                        'to': phone,
                        'text': message
                    })
                    
                    if response['messages'][0]['status'] == '0':
                        results.append({'phone': phone, 'success': True})
                    else:
                        results.append({
                            'phone': phone, 
                            'success': False, 
                            'error': response['messages'][0]['error-text']
                        })
                        
                except Exception as e:
                    results.append({'phone': phone, 'success': False, 'error': str(e)})
            
            success_count = sum(1 for r in results if r['success'])
            
            return {
                'success': success_count > 0,
                'results': results,
                'sent': success_count,
                'total': len(phone_numbers)
            }
            
        except Exception as e:
            self.logger.error(f"SMS sending failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_push(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send push notification via FCM"""
        if not self.fcm_server_key:
            return {'success': False, 'error': 'FCM server key not configured'}
        
        try:
            device_tokens = notification_data.get('device_tokens', [])
            if not device_tokens:
                return {'success': False, 'error': 'No device tokens provided'}
            
            headers = {
                'Authorization': f'key={self.fcm_server_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'registration_ids': device_tokens,
                'notification': {
                    'title': notification_data.get('subject', 'Smart Home Alert'),
                    'body': notification_data.get('message', ''),
                    'icon': 'ic_notification',
                    'sound': 'default'
                },
                'data': notification_data.get('data', {}),
                'priority': 'high' if notification_data.get('priority') == 'critical' else 'normal'
            }
            
            response = requests.post(
                self.fcm_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'sent': result.get('success', 0),
                    'failed': result.get('failure', 0),
                    'results': result.get('results', [])
                }
            else:
                return {
                    'success': False,
                    'error': f'FCM request failed: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.error(f"Push notification failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_websocket(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send real-time WebSocket notification"""
        if not self.socketio:
            return {'success': False, 'error': 'SocketIO not configured'}
        
        try:
            # Determine event type based on notification type
            event_name = 'notification'
            if notification_data.get('type') == 'alert':
                event_name = 'alert_notification'
            elif notification_data.get('type') == 'sensor_update':
                event_name = 'sensor_data_update'
            
            # Create WebSocket payload
            ws_payload = {
                'event': event_name,
                'notification': {
                    'id': f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'type': notification_data.get('type', 'info'),
                    'priority': notification_data.get('priority', 'medium'),
                    'subject': notification_data.get('subject', ''),
                    'message': notification_data.get('message', ''),
                    'timestamp': datetime.now().isoformat(),
                    'data': notification_data.get('data', {})
                }
            }
            
            # Emit to all connected clients
            self.socketio.emit(event_name, ws_payload)
            
            return {
                'success': True,
                'event': event_name,
                'message': 'WebSocket notification sent'
            }
            
        except Exception as e:
            self.logger.error(f"WebSocket notification failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_webhook(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook notification"""
        if not self.webhook_urls:
            return {'success': False, 'error': 'No webhook URLs configured'}
        
        try:
            webhook_payload = {
                'notification': notification_data,
                'timestamp': datetime.now().isoformat(),
                'source': 'smart_home_system'
            }
            
            results = []
            
            for webhook_url in self.webhook_urls:
                try:
                    response = requests.post(
                        webhook_url,
                        json=webhook_payload,
                        timeout=10,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    results.append({
                        'url': webhook_url,
                        'success': response.status_code < 400,
                        'status_code': response.status_code
                    })
                    
                except Exception as e:
                    results.append({
                        'url': webhook_url,
                        'success': False,
                        'error': str(e)
                    })
            
            success_count = sum(1 for r in results if r['success'])
            
            return {
                'success': success_count > 0,
                'results': results,
                'sent': success_count,
                'total': len(self.webhook_urls)
            }
            
        except Exception as e:
            self.logger.error(f"Webhook notification failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_email_recipients(self, recipients: List[str]) -> List[str]:
        """Filter email addresses from recipients list"""
        return [r for r in recipients if '@' in r]
    
    def _get_phone_recipients(self, recipients: List[str]) -> List[str]:
        """Filter phone numbers from recipients list"""
        return [r for r in recipients if r.startswith('+') or r.replace('-', '').replace(' ', '').isdigit()]
    
    def _create_email_html(self, notification_data: Dict[str, Any]) -> str:
        """Create HTML email content"""
        alert_data = notification_data.get('data', {})
        priority = notification_data.get('priority', 'medium')
        
        # Color scheme based on priority
        colors = {
            'low': '#28a745',
            'medium': '#ffc107', 
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        
        color = colors.get(priority, '#007bff')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .alert-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .timestamp {{ color: #6c757d; font-size: 0.9em; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 0.9em; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏠 Smart Home Alert</h1>
                    <p>Priority: {priority.upper()}</p>
                </div>
                <div class="content">
                    <h2>{notification_data.get('subject', 'Notification')}</h2>
                    <p>{notification_data.get('message', '')}</p>
                    
                    {self._create_alert_details_html(alert_data)}
                    
                    <div class="timestamp">
                        <strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                </div>
                <div class="footer">
                    <p>Smart Home Monitoring System</p>
                    <p>This is an automated notification. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_alert_details_html(self, alert_data: Dict[str, Any]) -> str:
        """Create HTML for alert details"""
        if not alert_data:
            return ""
        
        html = '<div class="alert-info"><h3>Alert Details</h3>'
        
        for key, value in alert_data.items():
            if key not in ['timestamp']:
                display_key = key.replace('_', ' ').title()
                html += f'<p><strong>{display_key}:</strong> {value}</p>'
        
        html += '</div>'
        return html
    
    def _create_sms_message(self, notification_data: Dict[str, Any]) -> str:
        """Create SMS message content"""
        subject = notification_data.get('subject', 'Smart Home Alert')
        message = notification_data.get('message', '')
        priority = notification_data.get('priority', '').upper()
        
        # Keep SMS short (160 chars max recommended)
        sms = f"🏠 {priority}: {subject}\n{message[:100]}..."
        
        return sms[:160]  # Truncate to SMS limit
    
    # Convenience methods for common notification types
    def send_alert_notification(self, alert: Dict[str, Any], channels: List[str] = None) -> Dict[str, Any]:
        """Send alert notification"""
        if channels is None:
            channels = ['websocket', 'email']
        
        notification_data = {
            'type': 'alert',
            'priority': alert.get('severity', 'medium').lower(),
            'subject': f"Smart Home Alert: {alert.get('type', 'Unknown')}",
            'message': alert.get('message', 'Alert triggered'),
            'recipients': self._get_default_recipients(),
            'channels': channels,
            'data': alert
        }
        
        return self.send_notification(notification_data)
    
    def send_sensor_update(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send sensor data update"""
        notification_data = {
            'type': 'sensor_update',
            'priority': 'low',
            'subject': 'Sensor Data Update',
            'message': f"Sensor data updated for {sensor_data.get('room', 'unknown room')}",
            'channels': ['websocket'],
            'data': sensor_data
        }
        
        return self.send_notification(notification_data)
    
    def send_system_notification(self, message: str, priority: str = 'medium') -> Dict[str, Any]:
        """Send system notification"""
        notification_data = {
            'type': 'system',
            'priority': priority,
            'subject': 'Smart Home System',
            'message': message,
            'recipients': self._get_default_recipients(),
            'channels': ['websocket', 'email']
        }
        
        return self.send_notification(notification_data)
    
    def _get_default_recipients(self) -> List[str]:
        """Get default notification recipients"""
        default_email = os.getenv('DEFAULT_NOTIFICATION_EMAIL')
        default_phone = os.getenv('DEFAULT_NOTIFICATION_PHONE')
        
        recipients = []
        if default_email:
            recipients.append(default_email)
        if default_phone:
            recipients.append(default_phone)
        
        return recipients 