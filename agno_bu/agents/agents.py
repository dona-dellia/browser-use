import os
from agno.agent import Agent, RunResponse
from browser_use.agent.views import AgentOutput
from agno_bu.agents.model import model
from textwrap import dedent
from agno_bu.agents.memory import memory
## TODO
## - change the instructions to browser-use
def createAgnoAgent(AgentOutput: AgentOutput) -> Agent:
    
    analyst: Agent = Agent(
        model=model,
        markdown=True,
        success_criteria="All requested steps executed successfully and all results confirmed",
        add_state_in_messages=True,
        memory=memory,
        enable_agentic_memory=True,
        user_id="Rodrigo",
        agent_id="analyst",
    #     description=dedent("""
    # You are a precise UI Quality Assurance Agent that interacts with websites through structured commands.

    #         You will receive from the user a list of action steps that should be executed in target application, but the key
    #         point is that we don't know if the steps provided by the user are practical executable in the application, because your job
    #         is to validate that the provided steps works. For that, you should try to execute the provided step by the user and
    #         check if the step is possible to be executed or if what the user said that should happen like 'display an error' indeed occured.

    #         In summary, try to the execute the steps provided by the user but not admit that those steps will work as expected, so try
    #         to execute them and validate its execution and if it's aligned with the user' list.

    #         If something occured different from what the user listed, like a error message that should be displayed in the page
    #         or some step could not be executed for any reason, like: according to the step a button should be clicked, but this
    #         button it's disabled you should immediately end the task.
            
    #         So, your role is to:
    #         1. Analyze the provided webpage elements and structure
    #         2. Use the given information to accomplish the ultimate task

    # 1. ACTIONS
    # - Multiple actions can be listed, executed in sequence.
    # - Only one action name per item.
    # Examples:
    # Form filling:
    # [
    # {"input_text": {"index": 1, "text": "username"}},
    # {"input_text": {"index": 2, "text": "password"}},
    # {"click_element": {"index": 3}}
    # ]
    # Navigation and extraction:
    # [
    # {"open_new_tab": {}},
    # {"go_to_url": {"url": "https://example.com"}},
    # {"extract_page_content": {}}
    # ]

    # 3. ELEMENT INTERACTION
    # - Only use indexes that exist in the provided list.
    # - Each element has a unique index (e.g., [33]<button>).

    # 4. NAVIGATION & ERROR HANDLING
    # - Only click buttons or links if the element exists, is visible, and matches the expected text or attributes.
    # - If missing → STOP and log the issue.
    # - Never guess or assume.
    # - If the task cannot continue: describe the issue and only then try:
    # - Go back to the previous page
    # - Perform a new search
    # - Open a new tab and retry
    # - Only accept/close popups or cookie banners if they truly appear.
    # - Use scrolling only if the element is present but not visible.

    # 7. FORM FILLING
    # - If a suggestion list appears after filling, select the correct suggestion before continuing.

    # 8. ACTION SEQUENCING
    # - Actions run in order.
    # - If the page changes after an action → sequence is interrupted.
    # - Chain actions only when page content remains static.

    # 10. EXTRACTION
    # - Use extract_page_content to capture data from specific pages.

    # 11. ASSERT
    # - Use assert_content to verify specific content presence.

    # 12. FAIL
    # - If failed more than once, try extract_content for help.

    # 13. CRITICAL DROPDOWN
    # - If a dropdown appears, make sure to only select the option asked, making sure that other options are not selected.
        
    #     """),

        instructions=dedent("""1. Choose the most appropriate action from the list of actions to accomplish the step.
                            2. just execute the action done when the ultimate task is accomplished. not the steps.
                            3. Choose only one action"""),
        response_model=AgentOutput,
    )
    return analyst


