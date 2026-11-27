from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat

EXPORT_MEDIA_TYPES = {
    ExportFormat.CSV: "text/csv",
    ExportFormat.XML: "application/xml",
}
