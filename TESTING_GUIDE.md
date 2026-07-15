# Testing Guide - Smart Scraping Feature

## Setup Steps

### 1. Apply Database Migration

**Option A: Via Supabase Dashboard**
1. Go to https://velgllhhzqnmhmuobcia.supabase.co
2. Navigate to SQL Editor
3. Run the following migration:

```sql
ALTER TABLE public.scrape_jobs 
ADD COLUMN IF NOT EXISTS crawl_mode text NOT NULL DEFAULT 'full_site' 
  CHECK (crawl_mode IN ('single_page', 'smart_crawl', 'full_site')),
ADD COLUMN IF NOT EXISTS selected_data_types jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS custom_selectors jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS preview_data jsonb DEFAULT '{}'::jsonb;
```

**Option B: Via Migration File**
```bash
# If using Supabase CLI
supabase db push
```

### 2. Start Services

Both services are already running:
- Worker: http://localhost:8000
- Frontend: http://localhost:3000

---

## Test Scenarios

### Test 1: LinkedIn Profile Search

**URL to test:**
```
https://www.linkedin.com/search/results/people/?keywords=data%20developer&origin=CLUSTER_EXPANSION
```

**Test Steps:**
1. Navigate to http://localhost:3000
2. Login with your credentials
3. Click "New Scrape Job"
4. Enter LinkedIn URL
5. Click "Preview" button
6. Wait 5-10 seconds

**Expected Results:**
- Should detect "LinkedIn Profile Cards"
- Shows count of profiles found (e.g., "25 items")
- Preview shows sample names/titles
- Pagination detected message appears
- Crawl mode auto-selects "Smart Crawl"

**Next Steps:**
7. Select "LinkedIn Profile Cards" (should be auto-selected)
8. Choose crawl mode (Single Page or Smart Crawl)
9. Click "Start Scraping"
10. Wait for completion

**Expected Data:**
- Name
- Title/Headline
- Company
- Location
- Profile URL

---

### Test 2: Wikipedia Article

**URLs to test:**
```
https://en.wikipedia.org/wiki/Artificial_intelligence
https://en.wikipedia.org/wiki/Python_(programming_language)
```

**Test Steps:**
1. Enter Wikipedia URL
2. Click "Preview"
3. Wait for detection

**Expected Results:**
- Detects "Wikipedia Article Content"
- Detects "Wikipedia Infobox" (if present)
- Shows section count
- Shows paragraph preview

**Next Steps:**
4. Select data types you want
5. Choose "Single Page" mode (recommended)
6. Start scraping

**Expected Data:**
- Article title
- Summary paragraphs
- Sections with headings
- Infobox data (structured key-value pairs)

---

### Test 3: Personal Portfolio

**URLs to test:**
```
https://www.maraich.me/
https://youssefel01.me/
```

**Test Steps:**
1. Enter portfolio URL
2. Click "Preview"
3. Wait for detection

**Expected Results:**
- May detect tables, cards, or content areas
- Shows preview of detected structures
- Single Page mode recommended

**What to Check:**
- Are projects/skills detected?
- Is contact information captured?
- Are unnecessary elements (nav, footer) excluded?

---

### Test 4: Generic Website with Tables

**Test URL:**
```
https://www.w3schools.com/html/html_tables.asp
```

**Expected Results:**
- Detects multiple tables
- Shows table headers and row counts
- Preview shows first few rows
- User can select specific tables

---

## What to Verify

### Preview Phase:
- [ ] Preview loads within 10 seconds
- [ ] Detected data structures are accurate
- [ ] Preview shows meaningful data samples
- [ ] Pagination detection works (if applicable)
- [ ] UI is responsive and clear

### Scraping Phase:
- [ ] Job starts immediately after submission
- [ ] Progress updates in real-time
- [ ] Scraping completes successfully
- [ ] Status shows "completed"
- [ ] No unnecessary data extracted

### Data Quality:
- [ ] Only selected data types are extracted
- [ ] Data is clean and well-structured
- [ ] No navigation/footer/boilerplate included
- [ ] Site-specific data (LinkedIn, Wikipedia) is properly parsed
- [ ] JSON export is valid and useful

---

## Common Issues & Solutions

### Issue 1: Preview Takes Too Long
**Cause:** Heavy JavaScript site or slow network
**Solution:** 
- Wait up to 30 seconds
- Check browser console for errors
- Try with a simpler website first

### Issue 2: No Data Detected
**Cause:** Page structure is too complex or non-standard
**Solution:**
- Try "Full Site" crawl mode
- Check if site requires authentication
- Look at the HTML source to understand structure

### Issue 3: LinkedIn Requires Login
**Cause:** LinkedIn blocks unauthenticated scrapers
**Solution:**
- This is expected behavior
- LinkedIn public search results should work without login
- For private profiles, authentication would be needed (future feature)

### Issue 4: Worker Not Responding
**Check:**
```bash
# Verify worker is running
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"healthy","service":"scrapestack-worker"}
```

---

## Performance Benchmarks

| Scenario | Mode | Expected Time | Pages Scraped |
|----------|------|---------------|---------------|
| Single Wikipedia article | Single Page | 5-10 seconds | 1 |
| LinkedIn search (1 page) | Single Page | 10-15 seconds | 1 |
| LinkedIn search (10 pages) | Smart Crawl | 2-3 minutes | 10 |
| Portfolio site | Single Page | 5-10 seconds | 1 |
| Full site crawl | Full Site | Varies | Up to max_pages |

---

## Success Criteria

Feature is working if:
1. Preview detects data on LinkedIn, Wikipedia, and portfolios
2. User can select what to scrape
3. Scraping completes without errors
4. Extracted data is clean and structured
5. Performance is significantly faster than old version
6. Single-page scrapes complete in <15 seconds

Issues to report:
1. Preview fails or times out
2. No data detected on known-good sites
3. Extracted data includes navigation/footers
4. Scraping job hangs or fails
5. UI is confusing or broken

---

## Test Report Template

```markdown
## Test Report - [Date/Time]

### Test 1: LinkedIn
- URL: [paste URL]
- Preview Result: PASS/FAIL
- Data Detected: [list what was detected]
- Scrape Result: PASS/FAIL
- Data Quality: [Good/Fair/Poor]
- Issues: [any problems]

### Test 2: Wikipedia
- URL: [paste URL]
- Preview Result: PASS/FAIL
- Data Detected: [list what was detected]
- Scrape Result: PASS/FAIL
- Data Quality: [Good/Fair/Poor]
- Issues: [any problems]

### Test 3: Portfolio
- URL: [paste URL]
- Preview Result: PASS/FAIL
- Data Detected: [list what was detected]
- Scrape Result: PASS/FAIL
- Data Quality: [Good/Fair/Poor]
- Issues: [any problems]

### Overall Assessment:
- Feature works: YES/NO
- Performance: [Fast/Acceptable/Slow]
- Data quality: [Excellent/Good/Fair/Poor]
- Ready for production: YES/NO
```

---

## Ready to Test!

1. Database migration applied
2. Worker running on port 8000
3. Frontend running on port 3000
4. Test URLs ready
5. Login credentials available

**Start testing at:** http://localhost:3000

**If you find any issues, check:**
- Browser console (F12)
- Worker logs (see terminal where worker is running)
- Network tab in DevTools
