# Multi-Agent Interoperability Demo

## Overview

This project demonstrates "Language-First Interoperability" between two specialized agents (Applicant and Administrator) that can communicate using multiple protocols while sharing a common conversation state. The system showcases real-time agent interactions for healthcare benefits eligibility processing, specifically focusing on BCSE (Benefits Coverage Support Eligibility) checking. The architecture supports switching between A2A JSON-RPC + SSE and MCP (Model Context Protocol) protocols seamlessly.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Web Interface**: Flask-based web application with real-time updates via Socket.IO
- **UI Framework**: Bootstrap with dark theme for responsive design
- **Real-time Communication**: WebSocket connections for live transcript viewing and protocol switching
- **Static Assets**: Organized JavaScript and CSS files for frontend functionality

### Backend Architecture
- **Application Framework**: Flask with Socket.IO for WebSocket support
- **Agent System**: Two specialized agents with distinct capabilities:
  - Applicant Agent: Handles patient eligibility applications and data gathering
  - Administrator Agent: Processes applications and makes eligibility determinations
- **Protocol Layer**: Dual protocol support with shared conversation core:
  - A2A (Agent-to-Agent): JSON-RPC 2.0 over HTTP with Server-Sent Events
  - MCP (Model Context Protocol): Tool-based interactions with streamable HTTP tools
- **Conversation Management**: Centralized memory system for persistent conversation state
- **Eligibility Engine**: BCSE eligibility checking with configurable rules and criteria

### Data Storage Solutions
- **In-Memory Storage**: Primary conversation storage with optional file persistence
- **JSON File Storage**: Patient data stored as JSON files for demo purposes
- **Thread-Safe Operations**: Conversation memory uses threading locks for concurrent access
- **Session Management**: UUID-based session tracking across protocols

### Authentication and Authorization
- **Session Security**: Flask session management with configurable secret keys
- **Agent Identity**: Card-based agent configuration with capability definitions
- **Security Compliance**: PII handling and audit logging for healthcare data

### Communication Protocols
- **A2A Protocol**: 
  - Methods: `initiate_eligibility_check`, `process_application`, `approve_application`
  - JSON-RPC 2.0 message format with unique request/response IDs
  - Server-Sent Events for real-time updates
- **MCP Protocol**:
  - Tools: `eligibility_check`, `process_application`, `get_patient_data`
  - Tool-based interaction model with structured parameters
  - Streamable HTTP tool execution

### Eligibility System
- **BCSE Rules Engine**: Configurable eligibility criteria including age, income, residency, employment status, and medical conditions
- **Multi-Factor Assessment**: Age requirements (18-65), income thresholds by family size, state residency validation
- **Medical Condition Support**: Chronic conditions and disability eligibility checking
- **Structured Results**: Detailed eligibility reports with pass/fail criteria and reasoning

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework for HTTP server and routing
- **Flask-SocketIO**: WebSocket support for real-time communication
- **Socket.IO Client**: JavaScript library for WebSocket connections

### Frontend Dependencies
- **Bootstrap**: UI framework with dark theme styling (via Replit CDN)
- **Feather Icons**: Icon library for UI elements
- **Socket.IO JavaScript Client**: Real-time communication with backend

### Development and Runtime
- **Python Standard Library**: JSON, logging, datetime, threading, uuid, os modules
- **File System**: Local JSON file storage for patient data and conversation persistence

### Protocol Standards
- **JSON-RPC 2.0**: Standard for A2A agent communication
- **Server-Sent Events**: HTTP standard for real-time data streaming
- **Model Context Protocol (MCP)**: Tool-based agent interaction standard
- **WebSocket Protocol**: Real-time bidirectional communication for web interface