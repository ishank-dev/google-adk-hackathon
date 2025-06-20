# Ella Bot - Knowledge Base Commands Usage Guide

## Overview

The Ella bot provides intelligent document management for your Slack workspace, allowing you to save conversations, notes, and documentation directly to a searchable knowledge base.

---

## 🔍 **Query Commands**

### `/ask_ella` - Ask Questions

Query the knowledge base for information.

**Syntax:**

```
/ask_ella [--anonymous|-a] <your question>
```

**Options:**

- `--anonymous` or `-a`: Ask the question anonymously

**Examples:**

```bash
/ask_ella How do we deploy to production?
/ask_ella -a What's our vacation policy?
/ask_ella --anonymous Who should I contact for IT issues?
```

---

## 📄 **Document Addition Commands**

### `/add_to_document` - Add Standalone Content

Add content directly via slash command (works in channels, not threads).

**Syntax:**

```
/add_to_document [-t title] [-c category] [-f] <content>
```

**Options:**

- `-t, --title`: Custom title for the document
- `-c, --category`: Category/doc_type for organization
- `-f, --force`: Skip AI relevance checking and force addition

**Examples:**

```bash
# Basic usage
/add_to_document Remember to update SSL certificates monthly

# With title and category
/add_to_document -t "SSL Maintenance" -c "processes" Update SSL certificates on the 1st of each month

# Force addition (skip relevance check)
/add_to_document -f -t "Random Notes" -c "misc" This might not be relevant but save it anyway
```

---

## 💬 **Thread-Based Commands**

### `@ella add_doc` - Capture Thread Conversations

Save entire thread conversations to the knowledge base (works everywhere).

**Syntax:**

```
@ella add_doc [title="..."] [category="..."] [force] <optional additional context>
```

**Options:**

- `title="..."`: Custom title (use quotes)
- `category="..."`: Category for organization (use quotes)
- `force`: Skip AI relevance checking
- Additional context: Extra information to include

**Alternative Commands:**

- `@ella add-doc`
- `@ella adddoc`
- `@ella save_thread`
- `@ella save-thread`

**Examples:**

#### Basic Thread Capture

```
[In a thread about deployment issues]
@ella add_doc title="Deployment Troubleshooting" category="processes"
```

_Captures the entire thread conversation with the specified title and category._

#### With Additional Context

```
[In a thread about API changes]
@ella add_doc title="API v2 Migration" category="documentation" This thread covers all the breaking changes we need to document for the v2 release
```

_Captures thread + adds extra context._

#### Force Addition

```
[Any thread]
@ella add_doc force title="Meeting Notes" category="meetings"
```

_Skips AI relevance checking and saves regardless of content quality._

#### Standalone Mention

```
@ella add_doc title="Quick Reminder" category="notes" Don't forget to backup the database before the weekend
```

_Saves just the provided text (no thread context)._

---

## 📊 **Statistics Command**

### `/document_stats` - View Knowledge Base Stats

Get an overview of your knowledge base contents.

**Syntax:**

```
/document_stats
```

**Returns:**

- Total number of documents
- Breakdown by category/document type

---

## 🎯 **Smart Features**

### **Automatic Relevance Checking**

The bot uses AI to evaluate content before adding it to the knowledge base:

- **Score 60-100**: Content is automatically added
- **Score 0-59**: Content is rejected with explanation
- **Use `force`**: Skip checking entirely

### **Thread Context Capture**

When used in threads, the bot captures:

- ✅ All messages in the conversation
- ✅ Participant names and timestamps
- ✅ Complete discussion context
- ✅ Any additional context you provide

### **Visual Feedback**

The bot provides immediate feedback through reactions:

- ⏳ `hourglass_flowing_sand` - Processing
- ✅ `white_check_mark` - Successfully added
- 🚫 `no_entry_sign` - Content rejected
- ❌ `x` - Error occurred
- ⚠️ `warning` - Invalid command format

---

## 📁 **Category Organization**

Organize your knowledge base with categories:

**Common Categories:**

- `processes` - Workflows and procedures
- `documentation` - Technical docs and guides
- `meetings` - Meeting notes and decisions
- `troubleshooting` - Problem-solving guides
- `policies` - Company policies and rules
- `team_updates` - Team announcements
- `general` - Default category for misc content

---

## 🔧 **Advanced Usage**

### **Thread Capture Best Practices**

1. **End of Discussion**: Use the command after a meaningful discussion concludes
2. **Clear Titles**: Use descriptive titles that others can search for
3. **Proper Categories**: Choose relevant categories for better organization
4. **Additional Context**: Add context to explain the thread's importance

### **Content Guidelines**

The AI checks for:

- **Informational Value**: Does it help team members?
- **Work Relevance**: Is it related to work/processes/tools?
- **Completeness**: Is the information useful as-is?
- **Clarity**: Is it understandable?
- **Appropriateness**: Is it suitable for a professional knowledge base?

### **When to Use Force**

Use the `force` option when:

- Content is relevant but might score low
- Saving personal notes or reminders
- Capturing incomplete but important discussions
- Override AI decisions you disagree with

---

## 🚨 **Troubleshooting**

### **Command Not Working?**

1. Make sure you're mentioning the bot correctly: `@ella`
2. Check command spelling: `add_doc` (with underscore)
3. Use quotes around titles/categories: `title="My Title"`
4. Try the test command: `@ella test`

### **No Response?**

1. Check if bot has necessary permissions
2. Verify you're in a channel where the bot is present
3. Try a simple slash command first: `/document_stats`

### **Content Rejected?**

1. Add more context to make it more relevant
2. Use the `force` option if you believe it's important
3. Check the relevance score and feedback provided

---

## 📚 **Usage Examples by Scenario**

### **After a Problem-Solving Discussion**

```
[Thread: "Production deployment failed, here's how we fixed it..."]
@ella add_doc title="Production Deployment Fix - Database Migration Issue" category="troubleshooting" This thread contains the complete solution for the migration timeout problem we encountered on 2025-06-15
```

### **Documenting a New Process**

```
[Thread: Team discussing new code review process]
@ella save_thread title="New Code Review Process v2" category="processes"
```

### **Quick Note Addition**

```
/add_to_document -t "Office Closure" -c "announcements" Office will be closed December 24-26 for holidays
```

### **Capturing Meeting Decisions**

```
[Thread: Discussion about choosing new framework]
@ella add_doc title="Framework Decision - React vs Vue" category="meetings" Final decision and reasoning from today's architecture meeting
```

---

## 🎉 **Tips for Maximum Value**

1. **Be Descriptive**: Use clear, searchable titles
2. **Categorize Consistently**: Stick to a consistent set of categories
3. **Capture Complete Discussions**: Wait until threads conclude naturally
4. **Add Context**: Explain why the content is important
5. **Use Force Sparingly**: Let the AI help filter quality content
6. **Regular Stats Checks**: Use `/document_stats` to monitor your knowledge base growth

Your knowledge base becomes more valuable as you consistently capture important discussions and decisions! 🚀
