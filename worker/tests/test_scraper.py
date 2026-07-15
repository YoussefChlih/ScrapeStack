import unittest
from urllib.robotparser import RobotFileParser
from app.scraper import (
    normalize_url,
    is_same_domain,
    extract_page_data,
    can_fetch,
)

class TestScraper(unittest.TestCase):
    
    def test_normalize_url(self):
        self.assertEqual(normalize_url("HTTPS://EXAMPLE.COM/FOO/"), "https://example.com/foo")
        self.assertEqual(normalize_url("https://example.com/foo#bar"), "https://example.com/foo")
        self.assertEqual(normalize_url("  https://example.com/foo?q=1   "), "https://example.com/foo?q=1")
        self.assertEqual(normalize_url("https://example.com"), "https://example.com")

    def test_is_same_domain(self):
        self.assertTrue(is_same_domain("https://example.com/foo", "example.com"))
        self.assertTrue(is_same_domain("https://sub.example.com/bar", "example.com"))
        self.assertTrue(is_same_domain("https://example.com:8000/bar", "example.com"))
        self.assertFalse(is_same_domain("https://otherdomain.com/foo", "example.com"))

    def test_can_fetch_robots(self):
        # Setup a mock RobotFileParser
        rp = RobotFileParser()
        rp.parse([
            "User-agent: *",
            "Disallow: /private",
            "Disallow: /admin/",
            "Allow: /public",
        ])
        
        self.assertTrue(can_fetch(rp, "https://example.com/public"))
        self.assertTrue(can_fetch(rp, "https://example.com/foo"))
        self.assertFalse(can_fetch(rp, "https://example.com/private"))
        self.assertFalse(can_fetch(rp, "https://example.com/admin/settings"))

    def test_extract_page_data_quality(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="canonical" href="https://example.com/canonical-url" />
            <meta property="og:title" content="OpenGraph Title" />
            <meta property="og:description" content="OpenGraph Description" />
            <meta property="og:image" content="https://example.com/og.png" />
            <meta name="description" content="Original Description" />
            <title>Original Title</title>
        </head>
        <body>
            <header>
                <h1>Header Title</h1>
                <nav>
                    <a href="/about">About Us</a>
                </nav>
            </header>
            
            <main>
                <h1>Main Heading</h1>
                <p>This is the first paragraph of clean content.</p>
                <div style="display: none">This is hidden text.</div>
                <div style="visibility: hidden">This is also hidden.</div>
                <div aria-hidden="true">Hidden for screen readers.</div>
                <p>This is the second paragraph of clean content.</p>
                <script>console.log("javascript noise");</script>
                <style>body { color: red; }</style>
                
                <table>
                    <tr><th>Name</th><th>Value</th></tr>
                    <tr><td>Item 1</td><td>100</td></tr>
                </table>

                <img src="/img.png" alt="Test Image" />
            </main>

            <footer>
                <p>© 2026 Boilerplate Footer</p>
            </footer>
        </body>
        </html>
        """
        
        data = extract_page_data(html, "https://example.com/page", "example.com")
        
        # Verify title & descriptions are parsed
        self.assertEqual(data["title"], "Original Title")
        self.assertEqual(data["meta_description"], "Original Description")
        
        # Verify boilerplate header, nav, footer, script, styles, and hidden tags are removed from text
        self.assertNotIn("Header Title", data["body_text"])
        self.assertNotIn("About Us", data["body_text"])
        self.assertNotIn("Boilerplate Footer", data["body_text"])
        self.assertNotIn("javascript noise", data["body_text"])
        self.assertNotIn("hidden text", data["body_text"])
        self.assertNotIn("also hidden", data["body_text"])
        self.assertNotIn("screen readers", data["body_text"])
        
        # Verify clean content remains
        self.assertIn("This is the first paragraph of clean content.", data["body_text"])
        self.assertIn("This is the second paragraph of clean content.", data["body_text"])
        
        # Verify headings, links, images, tables are extracted correctly from the page
        self.assertTrue(any(h["text"] == "Main Heading" for h in data["headings"]))
        self.assertTrue(any(l["url"] == "https://example.com/about" for l in data["links"]))
        self.assertTrue(any(img["src"] == "https://example.com/img.png" for img in data["images"]))
        self.assertEqual(len(data["tables"]), 1)
        self.assertEqual(data["tables"][0]["rows"][1], ["Item 1", "100"])

        # Check metadata inclusion in meta_tags
        self.assertTrue(any(m["name"] == "canonical" and m["content"] == "https://example.com/canonical-url" for m in data["meta_tags"]))
        self.assertTrue(any(m["name"] == "og:title" and m["content"] == "OpenGraph Title" for m in data["meta_tags"]))

    def test_extract_page_data_og_fallback(self):
        # Test case where title & description are missing but og counterparts exist
        html = """
        <html>
        <head>
            <meta property="og:title" content="Fallback OG Title" />
            <meta property="og:description" content="Fallback OG Description" />
        </head>
        <body>
            <p>Content</p>
        </body>
        </html>
        """
        data = extract_page_data(html, "https://example.com", "example.com")
        self.assertEqual(data["title"], "Fallback OG Title")
        self.assertEqual(data["meta_description"], "Fallback OG Description")

if __name__ == "__main__":
    unittest.main()
