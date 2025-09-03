import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading

logger = logging.getLogger(__name__)

class ConversationMemory:
    """In-memory conversation storage with optional persistence"""
    
    def __init__(self, persist_to_file: bool = True):
        self.conversations = {}
        self.persist_to_file = persist_to_file
        self.storage_path = "conversations_storage.json"
        self.lock = threading.RLock()
        
        # Load existing conversations if available
        if self.persist_to_file:
            self._load_conversations()
        
        logger.info("Conversation Memory initialized")
    
    def store_conversation(self, session_id: str, conversation_data: Dict[str, Any]) -> bool:
        """Store a new conversation"""
        try:
            with self.lock:
                self.conversations[session_id] = conversation_data.copy()
                
                if self.persist_to_file:
                    self._persist_conversations()
                
                logger.info(f"Stored conversation: {session_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error storing conversation {session_id}: {str(e)}")
            return False
    
    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation by session ID"""
        try:
            with self.lock:
                conversation = self.conversations.get(session_id)
                if conversation:
                    return conversation.copy()
                return None
        
        except Exception as e:
            logger.error(f"Error retrieving conversation {session_id}: {str(e)}")
            return None
    
    def update_conversation(self, session_id: str, conversation_data: Dict[str, Any]) -> bool:
        """Update an existing conversation"""
        try:
            with self.lock:
                if session_id in self.conversations:
                    self.conversations[session_id] = conversation_data.copy()
                    
                    if self.persist_to_file:
                        self._persist_conversations()
                    
                    logger.debug(f"Updated conversation: {session_id}")
                    return True
                else:
                    logger.warning(f"Conversation {session_id} not found for update")
                    return False
        
        except Exception as e:
            logger.error(f"Error updating conversation {session_id}: {str(e)}")
            return False
    
    def add_message(self, session_id: str, agent: str, message: Dict[str, Any], message_type: str = "message") -> bool:
        """Add a message to an existing conversation"""
        try:
            with self.lock:
                if session_id not in self.conversations:
                    logger.warning(f"Conversation {session_id} not found")
                    return False
                
                message_entry = {
                    "agent": agent,
                    "type": message_type,
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.conversations[session_id]["messages"].append(message_entry)
                self.conversations[session_id]["last_updated"] = datetime.now().isoformat()
                
                if self.persist_to_file:
                    self._persist_conversations()
                
                logger.debug(f"Added message to conversation {session_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error adding message to conversation {session_id}: {str(e)}")
            return False
    
    def add_artifact(self, session_id: str, artifact: Dict[str, Any]) -> bool:
        """Add an artifact to a conversation"""
        try:
            with self.lock:
                if session_id not in self.conversations:
                    logger.warning(f"Conversation {session_id} not found")
                    return False
                
                artifact_entry = {
                    "id": artifact.get("id", f"artifact_{len(self.conversations[session_id].get('artifacts', []))}"),
                    "type": artifact.get("type", "unknown"),
                    "data": artifact.get("data", {}),
                    "created_at": datetime.now().isoformat()
                }
                
                if "artifacts" not in self.conversations[session_id]:
                    self.conversations[session_id]["artifacts"] = []
                
                self.conversations[session_id]["artifacts"].append(artifact_entry)
                self.conversations[session_id]["last_updated"] = datetime.now().isoformat()
                
                if self.persist_to_file:
                    self._persist_conversations()
                
                logger.info(f"Added artifact to conversation {session_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error adding artifact to conversation {session_id}: {str(e)}")
            return False
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations with summary information"""
        try:
            with self.lock:
                summaries = []
                
                for session_id, conversation in self.conversations.items():
                    summary = {
                        "session_id": session_id,
                        "protocol": conversation.get("protocol", "unknown"),
                        "scenario": conversation.get("scenario", "unknown"),
                        "started_at": conversation.get("started_at"),
                        "last_updated": conversation.get("last_updated"),
                        "message_count": len(conversation.get("messages", [])),
                        "artifact_count": len(conversation.get("artifacts", []))
                    }
                    summaries.append(summary)
                
                # Sort by last updated (most recent first)
                summaries.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
                
                return summaries
        
        except Exception as e:
            logger.error(f"Error retrieving all conversations: {str(e)}")
            return []
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from a specific conversation"""
        try:
            with self.lock:
                conversation = self.conversations.get(session_id)
                if not conversation:
                    return []
                
                messages = conversation.get("messages", [])
                
                if limit:
                    messages = messages[-limit:]
                
                return messages.copy()
        
        except Exception as e:
            logger.error(f"Error retrieving messages for {session_id}: {str(e)}")
            return []
    
    def get_artifacts(self, session_id: str) -> List[Dict[str, Any]]:
        """Get artifacts from a specific conversation"""
        try:
            with self.lock:
                conversation = self.conversations.get(session_id)
                if not conversation:
                    return []
                
                return conversation.get("artifacts", []).copy()
        
        except Exception as e:
            logger.error(f"Error retrieving artifacts for {session_id}: {str(e)}")
            return []
    
    def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation"""
        try:
            with self.lock:
                if session_id in self.conversations:
                    del self.conversations[session_id]
                    
                    if self.persist_to_file:
                        self._persist_conversations()
                    
                    logger.info(f"Deleted conversation: {session_id}")
                    return True
                else:
                    logger.warning(f"Conversation {session_id} not found for deletion")
                    return False
        
        except Exception as e:
            logger.error(f"Error deleting conversation {session_id}: {str(e)}")
            return False
    
    def clear_all_conversations(self) -> bool:
        """Clear all conversations from memory"""
        try:
            with self.lock:
                self.conversations.clear()
                
                if self.persist_to_file:
                    self._persist_conversations()
                
                logger.info("All conversations cleared")
                return True
        
        except Exception as e:
            logger.error(f"Error clearing conversations: {str(e)}")
            return False
    
    def _load_conversations(self):
        """Load conversations from persistent storage"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self.conversations = json.load(f)
                logger.info(f"Loaded {len(self.conversations)} conversations from storage")
            else:
                logger.info("No existing conversation storage found")
        
        except Exception as e:
            logger.error(f"Error loading conversations: {str(e)}")
            self.conversations = {}
    
    def _persist_conversations(self):
        """Persist conversations to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.conversations, f, indent=2, default=str)
            logger.debug("Conversations persisted to storage")
        
        except Exception as e:
            logger.error(f"Error persisting conversations: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        with self.lock:
            total_conversations = len(self.conversations)
            total_messages = sum(len(conv.get("messages", [])) for conv in self.conversations.values())
            total_artifacts = sum(len(conv.get("artifacts", [])) for conv in self.conversations.values())
            
            protocols = {}
            for conv in self.conversations.values():
                protocol = conv.get("protocol", "unknown")
                protocols[protocol] = protocols.get(protocol, 0) + 1
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_artifacts": total_artifacts,
                "protocols": protocols,
                "storage_enabled": self.persist_to_file
            }
