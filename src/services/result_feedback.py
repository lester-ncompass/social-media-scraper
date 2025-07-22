import logging

import google.generativeai as genai

from src.core.config import config


class ResultFeedbackService:
    def __init__(self):
        self.logger = logging.getLogger("ResultFeedbackService")
        self.SYSTEM_INSTRUCTION_TEXT = ""
        """Loads the preprompt from a text file."""
        try:
            with open(config.PREPROMPT_FILE_PATH, "r", encoding="utf-8") as f:
                self.SYSTEM_INSTRUCTION_TEXT = f.read().strip()
        except FileNotFoundError:
            self.logger.error(
                "Preprompt file not found at {config.PREPROMPT_FILE_PATH}"
            )
            raise
        except Exception as e:
            self.logger.error("Could not read preprompt file: %s", e)
            raise
        if not config.GOOGLE_API_KEY:
            raise Exception("GOOGLE_API_KEY environment variable not set.")

    async def generate_feedback(
        self,
        raw_data: dict,
        scores: dict,
        text_model: str = config.TEXT_PROMPT_MODEL_NAME,
        **kwargs,
    ) -> str:
        """Generates an feedback based on structured data using Gemini SDK.

        Args:
            raw_data (dict): The raw data to generate feedback about.
            scores (dict): The scores to generate feedback about.
            text_model (str, optional): The model name to use for text generation.
                Defaults to config.TEXT_PROMPT_MODEL_NAME.

        Returns:
            str: The constructed feedback.
        """
        log = self.logger.getChild("generate_feedback")
        genai.configure(api_key=config.GOOGLE_API_KEY)
        user_prompt = "Here is the resulting data that you will be analyzing:"
        user_prompt = user_prompt + f"\n---\n{raw_data}{scores}\n---\n"
        user_prompt = (
            user_prompt
            + ":Generate the feedback based on this data and your instructions."
        )

        try:
            generative_model = genai.GenerativeModel(
                model_name=text_model,
                system_instruction=self.SYSTEM_INSTRUCTION_TEXT,
            )

            generation_config = genai.types.GenerationConfig(temperature=1.0)
            response = await generative_model.generate_content_async(
                user_prompt,
                generation_config=generation_config,
            )

            if response.parts:
                generated_feedback = "".join(
                    part.text for part in response.parts
                ).strip()
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason_msg = (
                        response.prompt_feedback.block_reason_message
                        or response.prompt_feedback.block_reason
                    )
                    log.warning("Prompt was blocked. Reason: %s", block_reason_msg)
                    raise Exception(f"Prompt generation blocked ({block_reason_msg})")
                log.info("Successfully generated text prompt.")
                return generated_feedback
            elif hasattr(response, "text") and response.text:
                generated_feedback = response.text.strip()
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason_msg = (
                        response.prompt_feedback.block_reason_message
                        or response.prompt_feedback.block_reason
                    )
                    log.warning(
                        "Prompt (from response.text) was blocked. Reason: %s",
                        block_reason_msg,
                    )
                    raise Exception(f"Prompt generation blocked ({block_reason_msg})")
                log.info("Successfully generated text prompt.")
                return generated_feedback
            else:
                log.warning(
                    "Gemini response was empty or did not contain expected text parts."
                )
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason_msg = (
                        response.prompt_feedback.block_reason_message
                        or response.prompt_feedback.block_reason
                    )
                    raise Exception(
                        f"Error: Prompt generation blocked ({block_reason_msg})"
                    )
                raise Exception("Error: Could not extract text from Gemini response.")

        except Exception as e:
            raise Exception("Error generating feedback with Gemini: ", e)
