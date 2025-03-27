"""
工具函数模块
"""

from doc_processor.utils.chinese_utils import cn_to_arabic, extract_batch_number
from doc_processor.utils.display import (
    console,
    create_progress_bar,
    display_batch_verification,
    display_comparison,
    display_statistics,
    display_table,
    print_doc_tree,
    print_error,
    print_info,
    print_success,
    print_title,
    print_warning,
)
from doc_processor.utils.logging_utils import (
    create_default_logging_config,
    create_logger,
    setup_default_logging,
    setup_logging,
)
from doc_processor.utils.profiling import (
    TimingContext,
    get_memory_usage,
    profile_function,
    time_function,
)
from doc_processor.utils.text_utils import (
    clean_text,
    extract_count_from_text,
    process_car_info,
    validate_car_info,
)

__all__ = [
    # chinese_utils
    "cn_to_arabic",
    "extract_batch_number",
    # display
    "console",
    "create_progress_bar",
    "display_batch_verification",
    "display_comparison",
    "display_statistics",
    "display_table",
    "print_doc_tree",
    "print_error",
    "print_info",
    "print_success",
    "print_title",
    "print_warning",
    # logging_utils
    "create_default_logging_config",
    "create_logger",
    "setup_default_logging",
    "setup_logging",
    # profiling
    "TimingContext",
    "get_memory_usage",
    "profile_function",
    "time_function",
    # text_utils
    "clean_text",
    "extract_count_from_text",
    "process_car_info",
    "validate_car_info",
]
