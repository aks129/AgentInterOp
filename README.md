# Multi-Agent Interoperability Demo

A comprehensive demonstration of "Language-First Interoperability" featuring two agents (Applicant and Administrator) that can communicate using both A2A JSON-RPC + SSE and MCP (Model Context Protocol) protocols.

## Overview

This demo showcases how different agent communication protocols can share the same conversation core while maintaining protocol-specific implementations. The system demonstrates real-time agent interactions for healthcare benefits eligibility processing.

## Features

### Core Functionality
- **Dual Protocol Support**: Switch between A2A JSON-RPC + SSE and MCP protocols
- **Two Distinct Agents**: Applicant Agent and Administrator Agent with specialized capabilities  
- **Shared Conversation Core**: Common conversation state management across protocols
- **Real-time Web UI**: Live transcript viewing and protocol switching
- **BCSE Eligibility System**: Benefits Coverage Support Eligibility checking
- **Persistent Memory**: Conversation history and artifacts storage

### Protocols

#### A2A (Agent-to-Agent)
- JSON-RPC 2.0 over HTTP
- Server-Sent Events for real-time updates
- Methods: `initiate_eligibility_check`, `process_application`, `approve_application`

#### MCP (Model Context Protocol)  
- Streamable HTTP tools
- Tool-based interactions
- Tools: `eligibility_check`, `process_application`, `get_patient_data`

## Architecture

