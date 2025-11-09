# Prompts for Agent Testing

This document contains prompts for testing different agents during the workshop. If you're using the web app, clear the chat from the top-right corner each time you change the agent or switch between single-chat and group-chat modes.

## 🛡️ Content Safety Testing

Before testing agents, verify Content Safety is working:

### Test Safe Content
```
I love puppies and sunshine
```
**Expected:** ✅ Safe (Severity: 0)

### Test Borderline Content
```
I'm feeling frustrated and angry
```
**Expected:** May show low severity (1-2) but should pass

### Test with Frontend UI
1. Navigate to "Content Safety Testing" panel in sidebar
2. Enter test text in the textarea
3. Click "Scan Text"
4. View category severities and flags
5. Upload test images to scan for visual content

## Generic Agent

### Prompt 1
```
write about boston
```

### Prompt 2
```
summarize in one sentence
```

## People Agent

### Prompt 1
```
List employees who works from boston office
```

### Prompt 2
```
Email Udai that a borad meeting has been scheduled for next week.
```

## Knowledge Agent

### Prompt 1
```
what is the PTO policy for employees who works over 10 years
```

## Group Chat Prompt

### Prompt 1
```
Whats the PTO policy for 
```

### Prompt 2
```
Email Emily regarding the PTO policy