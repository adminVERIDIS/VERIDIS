# VERIDIS PDF conformity reports

`PDFRenderer` generates offline A4 CSRD conformity reports with Jinja2 templates
and Playwright PDF rendering. The report is fixed to 21 print sections:
cover, executive summary, dashboard, ESRS detail pages, action plan and
methodology.

```python
from services.pdf_generator import PDFRenderer

renderer = PDFRenderer(s3_client=s3_client)
document = await renderer.generate(rapport, analysis_result)

print(document.filename)
print(document.page_count)
print(document.url)
```

The renderer forbids external URLs in templates and inlines `styles/print.css`
before calling `page.pdf`. To store the PDF, pass an object exposing:

```python
async def upload_pdf(key: str, body: bytes, content_type: str) -> str:
    ...
```

For asynchronous production jobs, configure the Celery worker dependencies at
application startup:

```python
from services.pdf_generator import PDFRenderer
from workers.generate_pdf import PDFWorkerDependencies, configure_pdf_worker

configure_pdf_worker(
    PDFWorkerDependencies(
        repository=repository,
        renderer=PDFRenderer(s3_client=s3_client),
    )
)
```
