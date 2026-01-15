"""
More Golden Templates - Part 2
"""
from django.core.management.base import BaseCommand
from apps.code_library.models import LibraryItem


MORE_TEMPLATES = [
    {
        "name": "Real Estate Agency",
        "description": "Property listings, search, and agent contact",
        "keywords": ["real estate", "property", "realtor", "homes", "houses", "apartments", "listings", "broker"],
        "tags": ["realestate", "property", "business"],
        "code": '''// Golden Template: Real Estate
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");
  const agency = { name: "{{BUSINESS_NAME}}", tagline: "{{TAGLINE}}", phone: "(555) 789-0123" };

  const properties = [
    { id: 1, title: "Modern Downtown Condo", price: "$425,000", beds: 2, baths: 2, sqft: "1,200", image: "https://picsum.photos/seed/condo1/400/300" },
    { id: 2, title: "Family Home with Garden", price: "$650,000", beds: 4, baths: 3, sqft: "2,400", image: "https://picsum.photos/seed/house1/400/300" },
    { id: 3, title: "Luxury Penthouse", price: "$1,200,000", beds: 3, baths: 2, sqft: "1,800", image: "https://picsum.photos/seed/pent1/400/300" },
    { id: 4, title: "Cozy Starter Home", price: "$285,000", beds: 2, baths: 1, sqft: "950", image: "https://picsum.photos/seed/starter1/400/300" },
    { id: 5, title: "Waterfront Villa", price: "$890,000", beds: 5, baths: 4, sqft: "3,200", image: "https://picsum.photos/seed/villa1/400/300" },
    { id: 6, title: "Urban Loft", price: "$375,000", beds: 1, baths: 1, sqft: "800", image: "https://picsum.photos/seed/loft1/400/300" }
  ];

  const Navigation = () => (
    <nav className="bg-indigo-900 shadow-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 flex justify-between h-16 items-center">
        <span className="text-2xl font-bold text-white">{agency.name}</span>
        <div className="flex space-x-1">
          {["home", "listings", "about", "contact"].map(view => (
            <button key={view} onClick={() => setCurrentView(view)} className={`px-4 py-2 rounded-lg text-sm font-medium transition ${currentView === view ? "bg-indigo-600 text-white" : "text-indigo-200 hover:bg-indigo-800"}`}>
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="bg-gradient-to-r from-indigo-900 to-purple-900 text-white py-20">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h1 className="text-5xl font-bold mb-4">{agency.name}</h1>
        <p className="text-xl text-indigo-200 mb-8">{agency.tagline}</p>
        <button onClick={() => setCurrentView("listings")} className="bg-white text-indigo-900 px-8 py-3 rounded-lg font-semibold hover:bg-indigo-100 transition">
          Browse Properties
        </button>
      </div>
    </div>
  );

  const ListingsSection = () => (
    <div className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Featured Properties</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {properties.map(p => (
            <div key={p.id} className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition">
              <img src={p.image} alt={p.title} className="w-full h-48 object-cover" />
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-2">{p.title}</h3>
                <p className="text-2xl font-bold text-indigo-600 mb-3">{p.price}</p>
                <div className="flex justify-between text-gray-600 text-sm">
                  <span>{p.beds} Beds</span><span>{p.baths} Baths</span><span>{p.sqft} sqft</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const ContactSection = () => {
    const [form, setForm] = React.useState({ name: "", email: "", message: "" });
    const [sent, setSent] = React.useState(false);
    const submit = (e) => { e.preventDefault(); setSent(true); setTimeout(() => setSent(false), 3000); };
    return (
      <div className="py-16 bg-white">
        <div className="max-w-xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-8">Contact Us</h2>
          {sent && <div className="bg-green-100 text-green-700 p-4 rounded-lg mb-4">Message sent!</div>}
          <form onSubmit={submit} className="space-y-4">
            <input type="text" placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full p-3 border rounded-lg" required />
            <input type="email" placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="w-full p-3 border rounded-lg" required />
            <textarea placeholder="Message" value={form.message} onChange={e => setForm({...form, message: e.target.value})} className="w-full p-3 border rounded-lg" rows={4} required />
            <button type="submit" className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700">Send</button>
          </form>
        </div>
      </div>
    );
  };

  const Footer = () => (
    <footer className="bg-indigo-900 text-indigo-200 py-8 text-center">
      <p className="font-bold text-white">{agency.name}</p>
      <p>{agency.phone}</p>
      <p className="mt-4 text-sm text-indigo-400">Powered by Claude Opus 4.5 | Built with Faibric</p>
    </footer>
  );

  return (
    <div className="min-h-screen">
      <Navigation />
      {currentView === "home" && <><HeroSection /><ListingsSection /></>}
      {currentView === "listings" && <ListingsSection />}
      {currentView === "contact" && <ContactSection />}
      <Footer />
    </div>
  );
};
export default App;'''
    },
    {
        "name": "Portfolio Website",
        "description": "Creative portfolio for designers, photographers, artists",
        "keywords": ["portfolio", "photography", "design", "creative", "artist", "photographer", "designer", "gallery", "showcase"],
        "tags": ["portfolio", "creative", "personal"],
        "code": '''// Golden Template: Portfolio
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");
  const profile = { name: "{{BUSINESS_NAME}}", tagline: "{{TAGLINE}}", email: "hello@example.com" };

  const works = [
    { id: 1, title: "Brand Identity", category: "Branding", image: "https://picsum.photos/seed/work1/400/400" },
    { id: 2, title: "Website Design", category: "Web", image: "https://picsum.photos/seed/work2/400/400" },
    { id: 3, title: "Mobile App", category: "UI/UX", image: "https://picsum.photos/seed/work3/400/400" },
    { id: 4, title: "Photography", category: "Photo", image: "https://picsum.photos/seed/work4/400/400" },
    { id: 5, title: "Illustration", category: "Art", image: "https://picsum.photos/seed/work5/400/400" },
    { id: 6, title: "Motion Design", category: "Video", image: "https://picsum.photos/seed/work6/400/400" }
  ];

  const Navigation = () => (
    <nav className="fixed top-0 w-full bg-black/90 backdrop-blur z-50">
      <div className="max-w-6xl mx-auto px-4 flex justify-between h-16 items-center">
        <span className="text-xl font-bold text-white">{profile.name}</span>
        <div className="flex space-x-6">
          {["home", "work", "about", "contact"].map(view => (
            <button key={view} onClick={() => setCurrentView(view)} className={`text-sm font-medium transition ${currentView === view ? "text-white" : "text-gray-400 hover:text-white"}`}>
              {view.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="min-h-screen bg-black text-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4">{profile.name}</h1>
        <p className="text-xl text-gray-400 mb-8">{profile.tagline}</p>
        <button onClick={() => setCurrentView("work")} className="border border-white px-8 py-3 hover:bg-white hover:text-black transition">
          VIEW WORK
        </button>
      </div>
    </div>
  );

  const WorkSection = () => (
    <div className="min-h-screen bg-black py-20 pt-24">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-white text-center mb-12">Selected Work</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {works.map(w => (
            <div key={w.id} className="group relative overflow-hidden">
              <img src={w.image} alt={w.title} className="w-full aspect-square object-cover group-hover:scale-110 transition duration-500" />
              <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                <div className="text-center text-white">
                  <h3 className="text-xl font-bold">{w.title}</h3>
                  <p className="text-gray-300">{w.category}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const ContactSection = () => {
    const [form, setForm] = React.useState({ name: "", email: "", message: "" });
    const [sent, setSent] = React.useState(false);
    const submit = (e) => { e.preventDefault(); setSent(true); };
    return (
      <div className="min-h-screen bg-black py-20 pt-24 flex items-center">
        <div className="max-w-xl mx-auto px-4 w-full">
          <h2 className="text-3xl font-bold text-white text-center mb-8">Get In Touch</h2>
          {sent ? (
            <div className="text-center text-green-400">Thanks! I'll be in touch soon.</div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <input type="text" placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full p-3 bg-gray-900 border border-gray-700 rounded text-white" required />
              <input type="email" placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="w-full p-3 bg-gray-900 border border-gray-700 rounded text-white" required />
              <textarea placeholder="Message" value={form.message} onChange={e => setForm({...form, message: e.target.value})} className="w-full p-3 bg-gray-900 border border-gray-700 rounded text-white" rows={5} required />
              <button type="submit" className="w-full bg-white text-black py-3 font-semibold hover:bg-gray-200 transition">SEND MESSAGE</button>
            </form>
          )}
        </div>
      </div>
    );
  };

  const Footer = () => (
    <footer className="bg-black text-gray-500 py-8 text-center border-t border-gray-800">
      <p>&copy; 2026 {profile.name}</p>
      <p className="mt-2 text-sm">Powered by Claude Opus 4.5 | Built with Faibric</p>
    </footer>
  );

  return (
    <div>
      <Navigation />
      {currentView === "home" && <HeroSection />}
      {currentView === "work" && <WorkSection />}
      {currentView === "contact" && <ContactSection />}
      {currentView !== "home" && <Footer />}
    </div>
  );
};
export default App;'''
    },
    {
        "name": "SaaS Landing Page",
        "description": "Software product landing page with features and pricing",
        "keywords": ["saas", "software", "startup", "app", "product", "landing", "tech", "platform"],
        "tags": ["saas", "tech", "landing"],
        "code": '''// Golden Template: SaaS Landing
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");
  const product = { name: "{{BUSINESS_NAME}}", tagline: "{{TAGLINE}}" };

  const features = [
    { title: "Lightning Fast", desc: "Optimized for speed and performance", icon: "&#9889;" },
    { title: "Secure", desc: "Enterprise-grade security built-in", icon: "&#128274;" },
    { title: "Scalable", desc: "Grows with your business needs", icon: "&#128200;" },
    { title: "24/7 Support", desc: "Always here when you need us", icon: "&#128172;" }
  ];

  const plans = [
    { name: "Starter", price: "$9", features: ["5 Users", "10GB Storage", "Email Support"] },
    { name: "Pro", price: "$29", features: ["25 Users", "100GB Storage", "Priority Support", "API Access"], popular: true },
    { name: "Enterprise", price: "$99", features: ["Unlimited Users", "1TB Storage", "Dedicated Support", "Custom Integrations", "SLA"] }
  ];

  const Navigation = () => (
    <nav className="fixed top-0 w-full bg-white/95 backdrop-blur shadow-sm z-50">
      <div className="max-w-7xl mx-auto px-4 flex justify-between h-16 items-center">
        <span className="text-2xl font-bold bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">{product.name}</span>
        <div className="flex items-center space-x-6">
          {["features", "pricing"].map(view => (
            <button key={view} onClick={() => setCurrentView(view)} className="text-gray-600 hover:text-violet-600 font-medium">
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
          <button className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-700">Get Started</button>
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="pt-32 pb-20 bg-gradient-to-b from-violet-50 to-white">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">{product.tagline}</h1>
        <p className="text-xl text-gray-600 mb-8">The all-in-one platform that helps teams work smarter, not harder.</p>
        <div className="flex justify-center gap-4">
          <button className="bg-violet-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-violet-700">Start Free Trial</button>
          <button className="border border-gray-300 px-8 py-3 rounded-lg font-semibold hover:border-violet-600 hover:text-violet-600">Watch Demo</button>
        </div>
        <p className="mt-4 text-sm text-gray-500">No credit card required</p>
      </div>
    </div>
  );

  const FeaturesSection = () => (
    <div className="py-20 bg-white" id="features">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Why Choose {product.name}?</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((f, i) => (
            <div key={i} className="text-center p-6">
              <div className="text-4xl mb-4" dangerouslySetInnerHTML={{__html: f.icon}} />
              <h3 className="text-xl font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-600">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const PricingSection = () => (
    <div className="py-20 bg-gray-50" id="pricing">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">Simple Pricing</h2>
        <p className="text-center text-gray-600 mb-12">Choose the plan that's right for you</p>
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((p, i) => (
            <div key={i} className={`rounded-2xl p-8 ${p.popular ? "bg-violet-600 text-white shadow-xl scale-105" : "bg-white shadow-lg"}`}>
              {p.popular && <span className="bg-yellow-400 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full">POPULAR</span>}
              <h3 className="text-2xl font-bold mt-4">{p.name}</h3>
              <div className="my-4"><span className="text-4xl font-bold">{p.price}</span><span className={p.popular ? "text-violet-200" : "text-gray-500"}>/month</span></div>
              <ul className="space-y-3 mb-8">
                {p.features.map((f, j) => <li key={j} className="flex items-center"><span className="mr-2">&#10003;</span>{f}</li>)}
              </ul>
              <button className={`w-full py-3 rounded-lg font-semibold ${p.popular ? "bg-white text-violet-600" : "bg-violet-600 text-white"}`}>Get Started</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const Footer = () => (
    <footer className="bg-gray-900 text-gray-400 py-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <p className="font-bold text-white text-xl mb-4">{product.name}</p>
        <p className="mb-4">&copy; 2026 {product.name}. All rights reserved.</p>
        <p className="text-sm">Powered by Claude Opus 4.5 | Built with Faibric</p>
      </div>
    </footer>
  );

  return (
    <div>
      <Navigation />
      {currentView === "home" && <><HeroSection /><FeaturesSection /><PricingSection /></>}
      {currentView === "features" && <div className="pt-20"><FeaturesSection /></div>}
      {currentView === "pricing" && <div className="pt-20"><PricingSection /></div>}
      <Footer />
    </div>
  );
};
export default App;'''
    },
    {
        "name": "E-commerce Store",
        "description": "Online store with product grid and shopping cart",
        "keywords": ["ecommerce", "store", "shop", "products", "retail", "online", "shopping", "buy", "sell"],
        "tags": ["ecommerce", "retail", "business"],
        "code": '''// Golden Template: E-commerce
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");
  const [cart, setCart] = React.useState([]);
  const store = { name: "{{BUSINESS_NAME}}", tagline: "{{TAGLINE}}" };

  const products = [
    { id: 1, name: "Classic Tee", price: 29, image: "https://picsum.photos/seed/prod1/300/300", category: "Tops" },
    { id: 2, name: "Denim Jacket", price: 89, image: "https://picsum.photos/seed/prod2/300/300", category: "Outerwear" },
    { id: 3, name: "Canvas Sneakers", price: 65, image: "https://picsum.photos/seed/prod3/300/300", category: "Footwear" },
    { id: 4, name: "Leather Belt", price: 45, image: "https://picsum.photos/seed/prod4/300/300", category: "Accessories" },
    { id: 5, name: "Wool Sweater", price: 79, image: "https://picsum.photos/seed/prod5/300/300", category: "Tops" },
    { id: 6, name: "Chino Pants", price: 59, image: "https://picsum.photos/seed/prod6/300/300", category: "Bottoms" }
  ];

  const addToCart = (product) => setCart([...cart, product]);
  const removeFromCart = (id) => setCart(cart.filter((_, i) => i !== id));
  const cartTotal = cart.reduce((sum, p) => sum + p.price, 0);

  const Navigation = () => (
    <nav className="bg-white shadow sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 flex justify-between h-16 items-center">
        <span className="text-2xl font-bold">{store.name}</span>
        <div className="flex items-center space-x-6">
          <button onClick={() => setCurrentView("home")} className="text-gray-600 hover:text-black">Shop</button>
          <button onClick={() => setCurrentView("cart")} className="relative">
            <span className="text-gray-600 hover:text-black">Cart</span>
            {cart.length > 0 && <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">{cart.length}</span>}
          </button>
        </div>
      </div>
    </nav>
  );

  const ProductGrid = () => (
    <div className="py-12">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold mb-8">Our Products</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map(p => (
            <div key={p.id} className="bg-white rounded-lg shadow-lg overflow-hidden group">
              <div className="relative">
                <img src={p.image} alt={p.name} className="w-full h-64 object-cover group-hover:scale-105 transition" />
              </div>
              <div className="p-4">
                <span className="text-sm text-gray-500">{p.category}</span>
                <h3 className="font-semibold text-lg">{p.name}</h3>
                <div className="flex justify-between items-center mt-2">
                  <span className="text-xl font-bold">${p.price}</span>
                  <button onClick={() => addToCart(p)} className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800">Add to Cart</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const CartView = () => (
    <div className="py-12">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-3xl font-bold mb-8">Your Cart</h2>
        {cart.length === 0 ? (
          <p className="text-gray-500">Your cart is empty</p>
        ) : (
          <>
            <div className="space-y-4 mb-8">
              {cart.map((item, i) => (
                <div key={i} className="flex items-center justify-between bg-white p-4 rounded-lg shadow">
                  <div className="flex items-center space-x-4">
                    <img src={item.image} alt={item.name} className="w-16 h-16 object-cover rounded" />
                    <div>
                      <h3 className="font-semibold">{item.name}</h3>
                      <p className="text-gray-500">${item.price}</p>
                    </div>
                  </div>
                  <button onClick={() => removeFromCart(i)} className="text-red-500 hover:text-red-700">Remove</button>
                </div>
              ))}
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex justify-between text-xl font-bold mb-4">
                <span>Total</span>
                <span>${cartTotal}</span>
              </div>
              <button className="w-full bg-black text-white py-3 rounded-lg font-semibold hover:bg-gray-800">Checkout</button>
            </div>
          </>
        )}
      </div>
    </div>
  );

  const Footer = () => (
    <footer className="bg-gray-900 text-gray-400 py-8 mt-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <p className="font-bold text-white mb-2">{store.name}</p>
        <p className="text-sm">Powered by Claude Opus 4.5 | Built with Faibric</p>
      </div>
    </footer>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      {currentView === "home" && <ProductGrid />}
      {currentView === "cart" && <CartView />}
      <Footer />
    </div>
  );
};
export default App;'''
    },
    {
        "name": "Booking System",
        "description": "Appointment booking for services like salons, clinics, consultants",
        "keywords": ["booking", "appointment", "schedule", "salon", "spa", "clinic", "doctor", "dentist", "barber"],
        "tags": ["booking", "services", "business"],
        "code": '''// Golden Template: Booking System
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");
  const [selectedDate, setSelectedDate] = React.useState("");
  const [selectedTime, setSelectedTime] = React.useState("");
  const [selectedService, setSelectedService] = React.useState("");
  const [booked, setBooked] = React.useState(false);

  const business = { name: "{{BUSINESS_NAME}}", tagline: "{{TAGLINE}}", phone: "(555) 321-9876" };

  const services = [
    { id: 1, name: "Consultation", duration: "30 min", price: "$50" },
    { id: 2, name: "Standard Session", duration: "60 min", price: "$85" },
    { id: 3, name: "Premium Package", duration: "90 min", price: "$120" },
    { id: 4, name: "Express Service", duration: "15 min", price: "$25" }
  ];

  const times = ["9:00 AM", "10:00 AM", "11:00 AM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"];

  const Navigation = () => (
    <nav className="bg-rose-600 shadow sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 flex justify-between h-16 items-center">
        <span className="text-2xl font-bold text-white">{business.name}</span>
        <div className="flex space-x-4">
          {["home", "book", "services"].map(view => (
            <button key={view} onClick={() => setCurrentView(view)} className={`px-4 py-2 rounded text-sm font-medium ${currentView === view ? "bg-white text-rose-600" : "text-rose-100 hover:bg-rose-500"}`}>
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="bg-gradient-to-r from-rose-500 to-pink-500 text-white py-20">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h1 className="text-5xl font-bold mb-4">{business.name}</h1>
        <p className="text-xl text-rose-100 mb-8">{business.tagline}</p>
        <button onClick={() => setCurrentView("book")} className="bg-white text-rose-600 px-8 py-3 rounded-lg font-semibold hover:bg-rose-100">
          Book Appointment
        </button>
      </div>
    </div>
  );

  const BookingSection = () => (
    <div className="py-16 bg-gray-50">
      <div className="max-w-2xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8">Book Your Appointment</h2>
        {booked ? (
          <div className="bg-green-100 text-green-700 p-8 rounded-xl text-center">
            <div className="text-4xl mb-4">&#10003;</div>
            <h3 className="text-2xl font-bold mb-2">Booking Confirmed!</h3>
            <p>We'll see you on {selectedDate} at {selectedTime}</p>
            <button onClick={() => { setBooked(false); setSelectedDate(""); setSelectedTime(""); setSelectedService(""); }} className="mt-4 text-rose-600 underline">Book Another</button>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-lg p-8 space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Select Service</label>
              <select value={selectedService} onChange={e => setSelectedService(e.target.value)} className="w-full p-3 border rounded-lg">
                <option value="">Choose a service...</option>
                {services.map(s => <option key={s.id} value={s.name}>{s.name} - {s.duration} - {s.price}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Select Date</label>
              <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} className="w-full p-3 border rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Select Time</label>
              <div className="grid grid-cols-4 gap-2">
                {times.map(t => (
                  <button key={t} onClick={() => setSelectedTime(t)} className={`p-2 rounded border ${selectedTime === t ? "bg-rose-600 text-white border-rose-600" : "hover:border-rose-600"}`}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <button onClick={() => selectedService && selectedDate && selectedTime && setBooked(true)} disabled={!selectedService || !selectedDate || !selectedTime} className="w-full bg-rose-600 text-white py-3 rounded-lg font-semibold hover:bg-rose-700 disabled:bg-gray-300 disabled:cursor-not-allowed">
              Confirm Booking
            </button>
          </div>
        )}
      </div>
    </div>
  );

  const ServicesSection = () => (
    <div className="py-16 bg-white">
      <div className="max-w-4xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Our Services</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {services.map(s => (
            <div key={s.id} className="border rounded-xl p-6 hover:shadow-lg transition">
              <h3 className="text-xl font-semibold">{s.name}</h3>
              <p className="text-gray-500">{s.duration}</p>
              <p className="text-2xl font-bold text-rose-600 mt-2">{s.price}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const Footer = () => (
    <footer className="bg-gray-900 text-gray-400 py-8 text-center">
      <p className="font-bold text-white">{business.name}</p>
      <p>{business.phone}</p>
      <p className="mt-4 text-sm">Powered by Claude Opus 4.5 | Built with Faibric</p>
    </footer>
  );

  return (
    <div className="min-h-screen">
      <Navigation />
      {currentView === "home" && <><HeroSection /><ServicesSection /></>}
      {currentView === "book" && <BookingSection />}
      {currentView === "services" && <ServicesSection />}
      <Footer />
    </div>
  );
};
export default App;'''
    },
    {
        "name": "Dashboard Analytics",
        "description": "Business dashboard with charts and metrics",
        "keywords": ["dashboard", "analytics", "metrics", "data", "charts", "admin", "panel", "reports", "kpi"],
        "tags": ["dashboard", "analytics", "business"],
        "code": '''// Golden Template: Dashboard
const App = () => {
  const [period, setPeriod] = React.useState("7d");
  const app = { name: "{{BUSINESS_NAME}}" };

  const metrics = [
    { label: "Total Revenue", value: "$48,295", change: "+12.5%", positive: true },
    { label: "Active Users", value: "2,847", change: "+8.2%", positive: true },
    { label: "Conversion Rate", value: "3.24%", change: "-0.4%", positive: false },
    { label: "Avg. Order Value", value: "$156", change: "+5.7%", positive: true }
  ];

  const chartData = [
    { day: "Mon", value: 4200 }, { day: "Tue", value: 5100 }, { day: "Wed", value: 4800 },
    { day: "Thu", value: 6200 }, { day: "Fri", value: 5800 }, { day: "Sat", value: 7100 }, { day: "Sun", value: 6500 }
  ];

  const recentOrders = [
    { id: "#3241", customer: "John Smith", amount: "$245", status: "Completed" },
    { id: "#3240", customer: "Sarah Wilson", amount: "$189", status: "Processing" },
    { id: "#3239", customer: "Mike Johnson", amount: "$432", status: "Completed" },
    { id: "#3238", customer: "Emily Brown", amount: "$98", status: "Pending" }
  ];

  const maxVal = Math.max(...chartData.map(d => d.value));

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 flex justify-between h-16 items-center">
          <span className="text-xl font-bold text-gray-900">{app.name} Dashboard</span>
          <select value={period} onChange={e => setPeriod(e.target.value)} className="border rounded px-3 py-1">
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {metrics.map((m, i) => (
            <div key={i} className="bg-white rounded-xl shadow p-6">
              <p className="text-gray-500 text-sm">{m.label}</p>
              <p className="text-3xl font-bold mt-1">{m.value}</p>
              <p className={`text-sm mt-1 ${m.positive ? "text-green-600" : "text-red-600"}`}>{m.change} vs last period</p>
            </div>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Revenue Overview</h3>
            <div className="flex items-end justify-between h-48 border-b">
              {chartData.map((d, i) => (
                <div key={i} className="flex flex-col items-center w-full">
                  <div className="bg-indigo-500 rounded-t w-8" style={{height: (d.value / maxVal * 100) + "%"}} />
                  <span className="text-xs text-gray-500 mt-2">{d.day}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Recent Orders</h3>
            <div className="space-y-4">
              {recentOrders.map(o => (
                <div key={o.id} className="flex justify-between items-center border-b pb-3">
                  <div>
                    <p className="font-medium">{o.customer}</p>
                    <p className="text-sm text-gray-500">{o.id}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{o.amount}</p>
                    <span className={`text-xs px-2 py-1 rounded ${o.status === "Completed" ? "bg-green-100 text-green-700" : o.status === "Processing" ? "bg-blue-100 text-blue-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {o.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-gray-400 text-sm mt-8">Powered by Claude Opus 4.5 | Built with Faibric</p>
      </main>
    </div>
  );
};
export default App;'''
    },
]


class Command(BaseCommand):
    help = 'Create more golden templates'

    def handle(self, *args, **options):
        created = 0
        for t in MORE_TEMPLATES:
            item, was_created = LibraryItem.objects.update_or_create(
                name=t["name"], item_type="template",
                defaults={"description": t["description"], "code": t["code"], "keywords": t["keywords"],
                          "tags": t["tags"], "quality_score": 0.95, "is_active": True, "is_approved": True,
                          "is_public": True, "needs_review": False, "created_by": "admin", "source": "golden"}
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {t['name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated: {t['name']}"))
        self.stdout.write(self.style.SUCCESS(f"Done! Created: {created}"))
