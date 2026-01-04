#!/usr/bin/env python
"""Build clean, working apps for testing."""
import os
import sys

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')

import django
django.setup()

from apps.deployment.vercel_deployer import get_vercel_deployer

vercel = get_vercel_deployer()

# Portfolio
portfolio_code = '''
function App() {
  const projects = [
    { id: 1, title: "E-commerce Platform", tech: "React, Node.js", img: "https://picsum.photos/400/300?random=1" },
    { id: 2, title: "Mobile Banking App", tech: "React Native", img: "https://picsum.photos/400/300?random=2" },
    { id: 3, title: "AI Dashboard", tech: "Python, TensorFlow", img: "https://picsum.photos/400/300?random=3" },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="py-20 text-center">
        <h1 className="text-5xl font-bold mb-4">John Developer</h1>
        <p className="text-xl text-gray-400">Full Stack Engineer</p>
        <div className="flex justify-center gap-4 mt-6">
          <a href="#" className="px-6 py-2 bg-blue-600 rounded hover:bg-blue-700">Contact</a>
          <a href="#" className="px-6 py-2 border border-gray-600 rounded hover:bg-gray-800">Resume</a>
        </div>
      </header>
      
      <section className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold mb-8">Projects</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {projects.map((p) => (
            <div key={p.id} className="bg-gray-800 rounded-lg overflow-hidden">
              <img src={p.img} alt={p.title} className="w-full h-48 object-cover" />
              <div className="p-4">
                <h3 className="font-bold text-lg">{p.title}</h3>
                <p className="text-gray-400 text-sm">{p.tech}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      
      <footer className="text-center py-8 text-gray-500">
        <p>2024 John Developer</p>
      </footer>
    </div>
  );
}
'''

# E-commerce
ecommerce_code = '''
function App() {
  const [cart, setCart] = React.useState([]);
  
  const products = [
    { id: 1, name: "Wireless Headphones", price: 99, img: "https://picsum.photos/200/200?random=10" },
    { id: 2, name: "Smart Watch", price: 199, img: "https://picsum.photos/200/200?random=11" },
    { id: 3, name: "Laptop Stand", price: 49, img: "https://picsum.photos/200/200?random=12" },
    { id: 4, name: "USB-C Hub", price: 79, img: "https://picsum.photos/200/200?random=13" },
  ];

  const addToCart = (product) => {
    setCart([...cart, product]);
  };

  const removeFromCart = (index) => {
    const newCart = [...cart];
    newCart.splice(index, 1);
    setCart(newCart);
  };

  const total = cart.reduce((sum, item) => sum + item.price, 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-indigo-600">TechShop</h1>
          <div className="flex items-center gap-4">
            <span className="bg-indigo-100 text-indigo-600 px-3 py-1 rounded-full text-sm">
              Cart: {cart.length} items (${total})
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold mb-6">Products</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {products.map((product) => (
            <div key={product.id} className="bg-white rounded-lg shadow-sm overflow-hidden">
              <img src={product.img} alt={product.name} className="w-full h-40 object-cover" />
              <div className="p-4">
                <h3 className="font-medium">{product.name}</h3>
                <p className="text-lg font-bold text-indigo-600">${product.price}</p>
                <button
                  onClick={() => addToCart(product)}
                  className="mt-2 w-full py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition"
                >
                  Add to Cart
                </button>
              </div>
            </div>
          ))}
        </div>

        {cart.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-bold mb-4">Shopping Cart</h3>
            {cart.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center py-2 border-b">
                <span>{item.name}</span>
                <div className="flex items-center gap-4">
                  <span className="font-medium">${item.price}</span>
                  <button 
                    onClick={() => removeFromCart(idx)}
                    className="text-red-500 hover:text-red-700"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
            <div className="mt-4 text-right">
              <span className="text-xl font-bold">Total: ${total}</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
'''

# Blog
blog_code = '''
function App() {
  const [selectedPost, setSelectedPost] = React.useState(null);
  
  const posts = [
    { 
      id: 1, 
      title: "Getting Started with React", 
      excerpt: "Learn the basics of React and build your first component.",
      content: "React is a powerful library for building user interfaces. In this guide, we will walk through creating your first component, understanding JSX, and managing state with hooks.",
      author: "Jane Doe",
      date: "Dec 15, 2024"
    },
    { 
      id: 2, 
      title: "Modern CSS Techniques", 
      excerpt: "Explore Flexbox, Grid, and modern styling approaches.",
      content: "CSS has evolved significantly. Flexbox and Grid have revolutionized how we create layouts, making responsive design more intuitive than ever before.",
      author: "John Smith",
      date: "Dec 10, 2024"
    },
    { 
      id: 3, 
      title: "Building APIs with Node.js", 
      excerpt: "Create RESTful APIs using Express and Node.js.",
      content: "Node.js makes it easy to build fast, scalable APIs. Combined with Express, you can create powerful backend services in just a few lines of code.",
      author: "Bob Wilson",
      date: "Dec 5, 2024"
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Tech Blog</h1>
          <p className="text-gray-600">Insights and tutorials for developers</p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {selectedPost ? (
          <article className="bg-white rounded-lg shadow p-8">
            <button 
              onClick={() => setSelectedPost(null)}
              className="text-indigo-600 mb-4 hover:underline"
            >
              Back to posts
            </button>
            <h2 className="text-3xl font-bold mb-4">{selectedPost.title}</h2>
            <div className="text-gray-500 mb-6">
              By {selectedPost.author} | {selectedPost.date}
            </div>
            <p className="text-gray-700 leading-relaxed">{selectedPost.content}</p>
          </article>
        ) : (
          <div className="space-y-6">
            {posts.map((post) => (
              <article 
                key={post.id} 
                className="bg-white rounded-lg shadow p-6 cursor-pointer hover:shadow-md transition"
                onClick={() => setSelectedPost(post)}
              >
                <h2 className="text-xl font-bold text-gray-900 mb-2">{post.title}</h2>
                <p className="text-gray-600 mb-4">{post.excerpt}</p>
                <div className="text-sm text-gray-500">
                  By {post.author} | {post.date}
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
'''

# Weather app (with placeholder for real data)
weather_code = '''
function App() {
  const [city, setCity] = React.useState("New York");
  const [loading, setLoading] = React.useState(false);
  
  const weatherData = {
    "New York": { temp: 45, condition: "Cloudy", humidity: 65 },
    "Los Angeles": { temp: 72, condition: "Sunny", humidity: 40 },
    "Chicago": { temp: 38, condition: "Snow", humidity: 80 },
    "Miami": { temp: 78, condition: "Partly Cloudy", humidity: 75 },
  };

  const cities = Object.keys(weatherData);
  const weather = weatherData[city] || weatherData["New York"];

  const handleCityChange = (newCity) => {
    setLoading(true);
    setTimeout(() => {
      setCity(newCity);
      setLoading(false);
    }, 500);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-400 to-blue-600">
      <div className="max-w-md mx-auto pt-20 px-4">
        <div className="bg-white/90 backdrop-blur rounded-2xl shadow-xl p-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-6">Weather App</h1>
          
          <select 
            value={city}
            onChange={(e) => handleCityChange(e.target.value)}
            className="w-full p-3 rounded-lg border-2 border-gray-200 mb-6 focus:border-blue-500 focus:outline-none"
          >
            {cities.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-6xl font-bold text-gray-800 mb-2">{weather.temp}F</p>
              <p className="text-xl text-gray-600 mb-4">{weather.condition}</p>
              <p className="text-gray-500">Humidity: {weather.humidity}%</p>
            </div>
          )}
          
          <p className="mt-6 text-xs text-gray-400 text-center">
            Note: This is sample data. Connect an API for live weather.
          </p>
        </div>
      </div>
    </div>
  );
}
'''

# Deploy all
apps = [
    ("portfolio-v2", portfolio_code),
    ("ecommerce-v2", ecommerce_code),
    ("blog-v2", blog_code),
    ("weather-v2", weather_code),
]

print("Deploying clean apps...")
print("=" * 60)

results = []
for name, code in apps:
    print(f"Deploying {name}...")
    result = vercel.deploy_static_app(name, code)
    url = result.get("url", "FAILED")
    verified = result.get("verified", False)
    print(f"  URL: {url}")
    print(f"  Verified: {verified}")
    results.append((name, url, verified))
    print()

print("=" * 60)
print("SUMMARY:")
for name, url, verified in results:
    status = "OK" if verified else "ISSUE"
    print(f"[{status}] {name}: {url}")



