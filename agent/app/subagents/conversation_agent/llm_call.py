from typing import List, Dict
from openai import AsyncOpenAI

from app.subagents.conversation_agent.prompt import CONVERSATION_PROMPT


async def conversational_llm(messages: List[Dict[str, str]], context: str, openai_client: AsyncOpenAI) -> str:
    """
    Makes an asynchronous call to the OpenAI chat completion API with the provided messages.

    Args:
        messages (List[Dict[str, str]]): A list of message dictionaries for the conversation.
        context (str): The context to be used in the conversation.
        openai_client (AsyncOpenAI): An instance of the AsyncOpenAI client.

    Returns:
        str: The content of the response from the LLM.
    """
    response = await openai_client.responses.create(
        model="gpt-4.1-mini",
        instructions=CONVERSATION_PROMPT.format(contexto=context),
        input=messages,
        temperature=0.2,
    )
