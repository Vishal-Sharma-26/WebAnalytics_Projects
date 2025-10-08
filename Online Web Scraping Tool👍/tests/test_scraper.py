# Basic unit tests for scraper functions (requires pytest)
from scraper import allowed_to_scrape, scrape_url

def test_allowed_example():
    assert allowed_to_scrape('https://example.com') is True

def test_scrape_example():
    data = scrape_url('https://example.com')
    assert 'title' in data
    assert 'Example Domain' in data['title']