# AI Notes Markdown Rendering (Newlines and Formatting)

**Status:** `PROPOSED`  
**Category:** Frontend / UI / UX  

---

## 1. Problem Overview

When the LLM generates AI match notes, analyses, or candidate summaries, the model outputs structured Markdown text containing headers, bullet points, and bold emphasis. For example:

```markdown
# Candidate Match Analysis: Data Engineer
## Strengths
- **11+ years of progressive experience** as a Data Engineer, with current role as Lead Data Engineer at Pacific Life Insurance (Sep 2023 - Present)
- **Strong multi-cloud expertise** spanning AWS (Glue, S3, EMR, Redshift, Lambda, Athena, Step Functions), Azure (Data Factory, ADLS Gen2, Synapse), and GCP (BigQuery, Dataflow, Dataproc, Cloud Composer)
- **Hands-on experience with modern data platforms**: Databricks (PySpark, Delta Lake), Snowflake (data warehousing, Snowpipe, secure data sharing)
- **End-to-end ETL/ELT pipeline design and implementation** across structured, semi-structured, and unstructured data sources — a core data engineering competency
- **Strong data warehousing and modeling skills**: dimensional modeling (star/snowflake schemas), Redshift, Snowflake, Synapse, BigQuery
- **Big Data processing expertise**: Apache Spark, PySpark, Spark SQL, Delta Lake optimization (partitioning, Z-ordering, Auto Loader)
- **Infrastructure as Code and DevOps**: Terraform, CloudFormation, Git-based CI/CD pipelines (Azure DevOps)
- **Data quality, governance, and security**: role-based access control, secure data sharing, data
```

Currently, the UI displays this output as unparsed raw/plain text, losing line breaks, header hierarchy, and bold formatting (`**text**`), which makes the analysis difficult to read.

---

## 2. Proposed Solution

1. **Markdown / Rich Text Parser Integration**:
   - Parse markdown tokens in candidate match notes and SSE streamed insight chunks.
   - Render `#` and `##` as structured section headings.
   - Render `- ` bullet points as structured lists with proper line breaks.
   - Convert `**text**` and `*text*` asterisks to strong/bold and italicized typography.
2. **Whitespace and Newline Preservation**:
   - Ensure newline characters (`\n`) are respected and formatted with appropriate paragraph or list spacing instead of collapsing into a single continuous block.
3. **Safe Rendering**:
   - Ensure standard HTML/DOM sanitization (e.g. DOMPurify or equivalent lightweight parser) to prevent any XSS vulnerabilities from LLM output.
