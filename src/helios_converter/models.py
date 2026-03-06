from dataclasses import dataclass, field



@dataclass
class QueryMatch:
    query_text: str
    line_number: int
    quote_type: str  # 'single' | 'double' | 'triple_single' | 'triple_double'
    variable_name: str | None = None
    converted_query: str | None = None
    conversion_successful: bool = False
    conversion_error: str | None = None


@dataclass
class ConversionResult:
    file: str
    file_type: str  # 'Python' | 'SQL' | 'Config'
    output: str | None = None
    queries_processed: int = 0
    success: bool = True
    error: str | None = None
    changes: list[str] = field(default_factory=list)
