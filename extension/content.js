/*
 * HalluciGuard - AI Hallucination Detection Middleware
 * Copyright (C) 2026 HalluciGuard Contributors
 *
 * This program is free software: you can redistribute it and/or modify...
 */

// HalluciGuard Content Script
console.log("🛡️ HalluciGuard active");

let lastAnalyzedText = "";

async function checkNewMessages() {
  // Simple heuristic for ChatGPT/Claude message containers
  const messages = document.querySelectorAll('.agent-turn, [data-testid^="assistant-message"], .message-assistant');
  if (messages.length === 0) return;

  const lastMessage = messages[messages.length - 1];
  const text = lastMessage.innerText;

  if (text !== lastAnalyzedText && text.length > 20) {
    lastAnalyzedText = text;
    console.log("🔍 HalluciGuard: Analyzing new message...");
    
    try {
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text })
      });
      
      const data = await response.json();
      injectBadge(lastMessage, data);
    } catch (err) {
      console.error("❌ HalluciGuard: API Error", err);
    }
  }
}

function injectBadge(element, data) {
  let badge = element.querySelector('.halluci-guard-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.className = 'halluci-guard-badge';
    badge.style.padding = '4px 8px';
    badge.style.margin = '8px 0';
    badge.style.borderRadius = '4px';
    badge.style.fontSize = '12px';
    badge.style.fontWeight = 'bold';
    element.appendChild(badge);
  }

  const score = data.trust_score;
  const color = score > 0.8 ? '#4caf50' : (score > 0.5 ? '#ff9800' : '#f44336');
  badge.style.backgroundColor = color + '22';
  badge.style.color = color;
  badge.style.border = `1px solid ${color}`;
  badge.innerText = `🛡️ Trust Score: ${Math.round(score * 100)}% (${data.flagged_claims.length} flagged)`;
}

// Poll for changes
setInterval(checkNewMessages, 3000);
