from utils.logger_handler import logger

def log_tool_call(tool_name: str, args: dict, result: str = None, error: str = None):
    if error:
        logger.error(f"[tool call] {tool_name} failed: {error}")
    else:
        logger.info(f"[tool call] {tool_name} | args: {args}")
        if result:
            logger.debug(f"[tool call] {tool_name} | result: {str(result)[:200]}")
