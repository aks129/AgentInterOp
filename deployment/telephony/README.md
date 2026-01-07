# Telephony Deployment

This directory contains Docker Compose and configuration files for deploying
the telephony stack that enables AgentInterOp agents to make phone calls.

## Components

- **Asterisk PBX**: Core telephony engine handling SIP/TLS
- **Shim Server**: Bridges Asterisk to voice agent WebSockets
- **Certbot**: Automatic TLS certificate renewal

## Prerequisites

1. **AWS Account** with Chime SDK access
2. **EC2 Instance** (t3.medium or larger) with Elastic IP
3. **Domain Name** with DNS A record pointing to EC2
4. **Phone Number** provisioned in AWS Chime

## Quick Start

### 1. Set Up AWS Chime

```bash
# Create SIP Media Application in AWS Console
# - Region: us-east-1 (recommended)
# - Provision a phone number
# - Note the Voice Connector ID
```

### 2. Configure DNS

Create an A record pointing your domain to your EC2 Elastic IP:
```
voice.yourdomain.com -> 1.2.3.4
```

### 3. Generate TLS Certificates

```bash
# On your EC2 instance
sudo certbot certonly --standalone -d voice.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/voice.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/voice.yourdomain.com/privkey.pem ./certs/
```

### 4. Configure Environment

```bash
cp env.example .env
# Edit .env with your values:
# - ARI_PASS: Secure password for Asterisk ARI
# - VOICE_AGENT_WSS_URL: Your AgentInterOp WebSocket URL
# - DOMAIN: Your domain name
```

### 5. Update Asterisk Config

Edit `asterisk/pjsip.conf`:
- Replace `your-voice-connector-id` with your AWS Chime Voice Connector ID
- Update the CIDR match ranges for AWS Chime IPs

### 6. Deploy

```bash
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### 7. Configure AgentInterOp

Add to your main `.env`:
```
TELEPHONY_ENABLED=true
SHIM_SERVER_URL=http://localhost:8080
CALLER_ID=+15551234567
OPENAI_API_KEY=sk-your-key
```

## Testing

### Local Test Call

```bash
# Via API
curl -X POST http://localhost:8000/api/telephony/originate \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+15551234567",
    "agent_id": "colonoscopy_scheduler"
  }'
```

### Asterisk CLI

```bash
# Access Asterisk console
docker exec -it agentinterop-asterisk asterisk -rvvv

# Useful commands
> pjsip show endpoints
> core show channels
> ari show apps
```

## Monitoring

### Health Endpoints

- Shim Server: `http://localhost:8080/health`
- AgentInterOp Telephony: `http://localhost:8000/api/telephony/health`

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f asterisk
docker-compose logs -f shim-server
```

## Troubleshooting

### No Audio
- Check RTP port range is open (10000-10299 UDP)
- Verify AWS Security Group allows Chime IPs
- Check `direct_media=no` in pjsip.conf

### TLS Errors
- Verify certificates are valid and not expired
- Check certificate permissions
- Ensure TLS 1.2+ is configured

### Call Not Connecting
- Verify AWS Chime Voice Connector is active
- Check phone number is associated with Voice Connector
- Review Asterisk logs for SIP errors

## Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| EC2 t3.medium | ~$30 |
| AWS Chime Voice Connector | ~$1/phone + $0.004/min |
| OpenAI (STT/TTS) | ~$60/1000 min |
| **Total (1000 min)** | ~$100 |

## Security Notes

- ARI only binds to localhost
- All SIP traffic uses TLS 1.2+
- Certificates auto-renew via certbot
- RTP ports isolated per call
