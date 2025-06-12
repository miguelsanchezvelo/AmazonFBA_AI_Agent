import csv
import os

# Define mock market data
mock_products = [
    {
        "asin": "B0ABCDE001",
        "title": "Stainless Steel Mixing Bowl Set",
        "price": 25.99,
        "rating": 4.7,
        "reviews": 820,
        "bsr": 350,
        "link": "https://example.com/B0ABCDE001",
        "source": "serpapi",
        "score": "HIGH",
        "estimated": False,
    },
    {
        "asin": "B0ABCDE002",
        "title": "Non-Stick Frying Pan 12 Inch",
        "price": 32.50,
        "rating": 4.6,
        "reviews": 560,
        "bsr": 450,
        "link": "https://example.com/B0ABCDE002",
        "source": "serpapi",
        "score": "HIGH",
        "estimated": False,
    },
    {
        "asin": "B0ABCDE003",
        "title": "Adjustable Dumbbell Set 20lb",
        "price": 40.0,
        "rating": 4.2,
        "reviews": 210,
        "bsr": 900,
        "link": "https://example.com/B0ABCDE003",
        "source": "keepa",
        "score": "MEDIUM",
        "estimated": False,
    },
    {
        "asin": "B0ABCDE004",
        "title": "Yoga Mat Eco-Friendly 6mm",
        "price": 23.99,
        "rating": 4.1,
        "reviews": 150,
        "bsr": 1200,
        "link": "https://example.com/B0ABCDE004",
        "source": "keepa",
        "score": "MEDIUM",
        "estimated": False,
    },
    {
        "asin": "B0ABCDE005",
        "title": "Baby Swaddle Blanket",
        "price": 18.50,
        "rating": 4.5,
        "reviews": 300,
        "bsr": 1400,
        "link": "https://example.com/B0ABCDE005",
        "source": "serpapi",
        "score": "HIGH",
        "estimated": False,
    },
    {
        "asin": "B0ABCDE006",
        "title": "Portable Blender for Smoothies",
        "price": 29.99,
        "rating": 3.8,
        "reviews": 90,
        "bsr": 1800,
        "link": "https://example.com/B0ABCDE006",
        "source": "manual",
        "score": "LOW",
        "estimated": True,
    },
    {
        "asin": "B0ABCDE007",
        "title": "Cordless Handheld Vacuum",
        "price": 65.99,
        "rating": 4.4,
        "reviews": 430,
        "bsr": 320,
        "link": "https://example.com/B0ABCDE007",
        "source": "manual",
        "score": "HIGH",
        "estimated": True,
    },
    {
        "asin": "B0ABCDE008",
        "title": "Silicone Baking Mat 2 Pack",
        "price": 13.99,
        "rating": 4.3,
        "reviews": 270,
        "bsr": 1000,
        "link": "https://example.com/B0ABCDE008",
        "source": "keepa",
        "score": "MEDIUM",
        "estimated": False,
    },
    {
        "asin": "B0ABCDE009",
        "title": "Organic Cotton Baby Bibs Set",
        "price": 16.99,
        "rating": 4.0,
        "reviews": 80,
        "bsr": 2000,
        "link": "https://example.com/B0ABCDE009",
        "source": "serpapi",
        "score": "MEDIUM",
        "estimated": True,
    },
    {
        "asin": "B0ABCDE010",
        "title": "Electric Milk Frother Handheld",
        "price": 14.49,
        "rating": 4.6,
        "reviews": 512,
        "bsr": 600,
        "link": "https://example.com/B0ABCDE010",
        "source": "manual",
        "score": "HIGH",
        "estimated": False,
    },
]

def main() -> None:
    os.makedirs("data", exist_ok=True)
    output_file = os.path.join("data", "mock_market_data.csv")
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "asin",
                "title",
                "price",
                "rating",
                "reviews",
                "bsr",
                "link",
                "source",
                "score",
                "estimated",
            ],
        )
        writer.writeheader()
        writer.writerows(mock_products)
    print(f"Mock market data saved to {output_file}")


if __name__ == "__main__":
    main()
