# Idea

A natural faq store bot which allows users to know more about org. It could be a dev onboarding process, knowing about a product, upcoming event or resolving an error or technical issue or looking for documentation or process for requesting access:

1. Listen to all personal dms to bot and respond to them accordingly.
2. Listen to @ mentions to bot and reply in the same thread.
3. Use slash commands and then procceed with the conversation in the thread.
4. Use interactive UI buttons for more natural kind of flow for users
5. Anything else or combining some of the above ones.

## Approach

- We can allow users to start interactions with the following options:

  - `Ask a public query` - This allows users to have a conversation with the bot in public threads/groups/channels wherever they have initiated this.
  - `Ask a private query` - This will be acknowledged by the bot and then user will recieve a DM from the bot to continue the conversation privately. If user writes in the DM, it will be treated as a private query.
  - `Store a query` - This will only be allowed in a public or private thread. The bot will store the query and the response in a database for future reference.

### Additional Considerations

- When user asks a question, the bot at backend will use LLMs to ensure if the query is valid to be answered in public forum or not. If it is not, then it will ask the user to ask the question privately.
- The bot will also ask user to pick from one of the options to continue the conversation, this will help us refine and improve the bot's responses over time. Here are the available options:
  - Onboarding process
  - Product information
  - Upcoming events
  - Error resolution
  - Documentation
  - Access requests
- The bot will also have a feedback mechanism to allow users to rate the responses and provide suggestions for improvement.
