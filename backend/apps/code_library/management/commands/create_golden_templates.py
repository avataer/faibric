"""
Create Golden Templates - Pre-made complete apps for instant serving.

Per strategy: "The best AI app builder barely uses AI" - pre-generate templates.
"""
import uuid
from django.core.management.base import BaseCommand
from apps.code_library.models import LibraryItem


GOLDEN_TEMPLATES = [
    {
        "name": "Restaurant Website",
        "description": "Complete restaurant/cafe website with menu, about, and contact",
        "keywords": ["restaurant", "cafe", "food", "menu", "dining", "bakery", "pizza", "coffee"],
        "tags": ["restaurant", "food", "business"],
        "code": '''// Golden Template: Restaurant Website
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");

  const restaurant = {
    name: "{{BUSINESS_NAME}}",
    tagline: "{{TAGLINE}}",
    phone: "(555) 123-4567",
    address: "123 Main Street, City, State 12345",
    hours: "Mon-Sun: 11am - 10pm"
  };

  const menuItems = [
    { id: 1, name: "Signature Dish", description: "Our chef's special creation", price: "$24", category: "Mains" },
    { id: 2, name: "Fresh Salad", description: "Organic greens with house dressing", price: "$12", category: "Starters" },
    { id: 3, name: "Grilled Salmon", description: "Atlantic salmon with seasonal vegetables", price: "$28", category: "Mains" },
    { id: 4, name: "Chocolate Cake", description: "Rich dark chocolate with berries", price: "$10", category: "Desserts" },
    { id: 5, name: "Craft Cocktail", description: "Handcrafted specialty drinks", price: "$14", category: "Drinks" },
    { id: 6, name: "Appetizer Platter", description: "Selection of house favorites", price: "$18", category: "Starters" }
  ];

  const Navigation = () => (
    <nav className="bg-gradient-to-r from-amber-900 via-amber-800 to-amber-900 shadow-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <span className="text-2xl font-bold text-amber-100">{restaurant.name}</span>
          <div className="flex space-x-1">
            {["home", "menu", "about", "contact"].map(view => (
              <button
                key={view}
                onClick={() => setCurrentView(view)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  currentView === view
                    ? "bg-amber-100 text-amber-900"
                    : "text-amber-100 hover:bg-amber-700"
                }`}
              >
                {view.charAt(0).toUpperCase() + view.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="relative bg-gradient-to-br from-amber-900 via-amber-800 to-amber-700 text-white py-24">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6">{restaurant.name}</h1>
        <p className="text-xl md:text-2xl text-amber-100 mb-8">{restaurant.tagline}</p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => setCurrentView("menu")}
            className="bg-white text-amber-900 px-8 py-3 rounded-full font-semibold hover:bg-amber-100 transition"
          >
            View Menu
          </button>
          <button
            onClick={() => setCurrentView("contact")}
            className="border-2 border-white px-8 py-3 rounded-full font-semibold hover:bg-white hover:text-amber-900 transition"
          >
            Reserve Table
          </button>
        </div>
      </div>
    </div>
  );

  const MenuSection = () => (
    <div className="py-16 bg-amber-50">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-4xl font-bold text-center text-amber-900 mb-12">Our Menu</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {menuItems.map(item => (
            <div key={item.id} className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-xl font-semibold text-amber-900">{item.name}</h3>
                <span className="text-lg font-bold text-amber-600">{item.price}</span>
              </div>
              <p className="text-gray-600 mb-2">{item.description}</p>
              <span className="text-sm text-amber-500 font-medium">{item.category}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const AboutSection = () => (
    <div className="py-16 bg-white">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h2 className="text-4xl font-bold text-amber-900 mb-8">About Us</h2>
        <p className="text-lg text-gray-600 mb-8">
          Welcome to {restaurant.name}, where culinary excellence meets warm hospitality.
          Our passionate chefs craft each dish with the finest ingredients, creating memorable
          dining experiences for our guests since 2010.
        </p>
        <div className="grid md:grid-cols-3 gap-8 mt-12">
          <div className="p-6">
            <div className="text-4xl mb-4">&#127860;</div>
            <h3 className="text-xl font-semibold text-amber-900 mb-2">Fresh Ingredients</h3>
            <p className="text-gray-600">Locally sourced, organic produce</p>
          </div>
          <div className="p-6">
            <div className="text-4xl mb-4">&#128104;&#8205;&#127859;</div>
            <h3 className="text-xl font-semibold text-amber-900 mb-2">Expert Chefs</h3>
            <p className="text-gray-600">Award-winning culinary team</p>
          </div>
          <div className="p-6">
            <div className="text-4xl mb-4">&#10084;&#65039;</div>
            <h3 className="text-xl font-semibold text-amber-900 mb-2">Made with Love</h3>
            <p className="text-gray-600">Passion in every plate</p>
          </div>
        </div>
      </div>
    </div>
  );

  const ContactSection = () => {
    const [formData, setFormData] = React.useState({ name: "", email: "", date: "", guests: "", message: "" });
    const [submitted, setSubmitted] = React.useState(false);

    const handleSubmit = (e) => {
      e.preventDefault();
      setSubmitted(true);
      setTimeout(() => setSubmitted(false), 3000);
    };

    return (
      <div className="py-16 bg-amber-50">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-center text-amber-900 mb-12">Reserve a Table</h2>
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <h3 className="text-2xl font-semibold text-amber-900 mb-6">Contact Info</h3>
              <div className="space-y-4 text-gray-600">
                <p><strong>Address:</strong> {restaurant.address}</p>
                <p><strong>Phone:</strong> {restaurant.phone}</p>
                <p><strong>Hours:</strong> {restaurant.hours}</p>
              </div>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              {submitted && (
                <div className="bg-green-100 text-green-700 p-4 rounded-lg mb-4">
                  Reservation request sent! We'll confirm shortly.
                </div>
              )}
              <input
                type="text"
                placeholder="Your Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full p-3 border border-amber-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
                required
              />
              <input
                type="email"
                placeholder="Email Address"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="w-full p-3 border border-amber-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
                required
              />
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({...formData, date: e.target.value})}
                  className="w-full p-3 border border-amber-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  required
                />
                <select
                  value={formData.guests}
                  onChange={(e) => setFormData({...formData, guests: e.target.value})}
                  className="w-full p-3 border border-amber-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  required
                >
                  <option value="">Guests</option>
                  {[1,2,3,4,5,6,7,8].map(n => <option key={n} value={n}>{n} {n === 1 ? "Guest" : "Guests"}</option>)}
                </select>
              </div>
              <textarea
                placeholder="Special requests..."
                value={formData.message}
                onChange={(e) => setFormData({...formData, message: e.target.value})}
                rows={3}
                className="w-full p-3 border border-amber-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
              <button
                type="submit"
                className="w-full bg-amber-600 text-white py-3 rounded-lg font-semibold hover:bg-amber-700 transition"
              >
                Request Reservation
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  };

  const Footer = () => (
    <footer className="bg-amber-900 text-amber-100 py-12">
      <div className="max-w-7xl mx-auto px-4">
        <div className="grid md:grid-cols-3 gap-8 mb-8">
          <div>
            <h3 className="text-xl font-bold text-white mb-4">{restaurant.name}</h3>
            <p className="text-amber-200">{restaurant.tagline}</p>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-4">Hours</h4>
            <p className="text-amber-200">{restaurant.hours}</p>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-4">Contact</h4>
            <p className="text-amber-200">{restaurant.phone}</p>
            <p className="text-amber-200">{restaurant.address}</p>
          </div>
        </div>
        <div className="border-t border-amber-800 pt-8 text-center text-amber-300">
          <p>&copy; 2026 {restaurant.name}. All rights reserved.</p>
          <p className="mt-2 text-sm">Powered by Claude Opus 4.5 | Built with Faibric</p>
        </div>
      </div>
    </footer>
  );

  return (
    <div className="min-h-screen bg-amber-50">
      <Navigation />
      {currentView === "home" && <HeroSection />}
      {currentView === "menu" && <MenuSection />}
      {currentView === "about" && <AboutSection />}
      {currentView === "contact" && <ContactSection />}
      {currentView === "home" && <MenuSection />}
      {currentView === "home" && <AboutSection />}
      <Footer />
    </div>
  );
};

export default App;'''
    },
    {
        "name": "Professional Services",
        "description": "Law firm, consulting, or professional services website",
        "keywords": ["lawyer", "attorney", "law", "consulting", "consultant", "accountant", "professional", "legal", "financial"],
        "tags": ["professional", "services", "business"],
        "code": '''// Golden Template: Professional Services
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");

  const business = {
    name: "{{BUSINESS_NAME}}",
    tagline: "{{TAGLINE}}",
    phone: "(555) 987-6543",
    email: "contact@example.com",
    address: "456 Business Ave, Suite 100, City, State 12345"
  };

  const services = [
    { id: 1, title: "Consultation", description: "Expert guidance tailored to your needs", icon: "&#128172;" },
    { id: 2, title: "Strategy", description: "Comprehensive planning and analysis", icon: "&#128200;" },
    { id: 3, title: "Implementation", description: "Hands-on support for your goals", icon: "&#9989;" },
    { id: 4, title: "Review", description: "Thorough assessment and recommendations", icon: "&#128269;" }
  ];

  const Navigation = () => (
    <nav className="bg-slate-900 shadow-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <span className="text-2xl font-bold text-white">{business.name}</span>
          <div className="flex space-x-1">
            {["home", "services", "about", "contact"].map(view => (
              <button
                key={view}
                onClick={() => setCurrentView(view)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  currentView === view
                    ? "bg-blue-600 text-white"
                    : "text-gray-300 hover:bg-slate-800"
                }`}
              >
                {view.charAt(0).toUpperCase() + view.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 text-white py-24">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6">{business.name}</h1>
        <p className="text-xl md:text-2xl text-blue-200 mb-8 max-w-3xl mx-auto">{business.tagline}</p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => setCurrentView("contact")}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            Free Consultation
          </button>
          <button
            onClick={() => setCurrentView("services")}
            className="border-2 border-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-slate-900 transition"
          >
            Our Services
          </button>
        </div>
      </div>
    </div>
  );

  const ServicesSection = () => (
    <div className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-4xl font-bold text-center text-slate-900 mb-12">Our Services</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {services.map(service => (
            <div key={service.id} className="bg-white rounded-xl shadow-lg p-8 text-center hover:shadow-xl transition hover:-translate-y-1">
              <div className="text-4xl mb-4" dangerouslySetInnerHTML={{__html: service.icon}} />
              <h3 className="text-xl font-semibold text-slate-900 mb-2">{service.title}</h3>
              <p className="text-gray-600">{service.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const AboutSection = () => (
    <div className="py-16 bg-white">
      <div className="max-w-4xl mx-auto px-4">
        <h2 className="text-4xl font-bold text-center text-slate-900 mb-8">About Us</h2>
        <p className="text-lg text-gray-600 text-center mb-12">
          With decades of combined experience, {business.name} provides exceptional service
          to clients across all industries. Our commitment to excellence and personalized
          attention sets us apart.
        </p>
        <div className="grid md:grid-cols-3 gap-8 text-center">
          <div className="p-6">
            <div className="text-4xl font-bold text-blue-600 mb-2">500+</div>
            <p className="text-gray-600">Clients Served</p>
          </div>
          <div className="p-6">
            <div className="text-4xl font-bold text-blue-600 mb-2">25+</div>
            <p className="text-gray-600">Years Experience</p>
          </div>
          <div className="p-6">
            <div className="text-4xl font-bold text-blue-600 mb-2">98%</div>
            <p className="text-gray-600">Client Satisfaction</p>
          </div>
        </div>
      </div>
    </div>
  );

  const ContactSection = () => {
    const [formData, setFormData] = React.useState({ name: "", email: "", phone: "", message: "" });
    const [submitted, setSubmitted] = React.useState(false);

    const handleSubmit = (e) => {
      e.preventDefault();
      setSubmitted(true);
      setTimeout(() => setSubmitted(false), 3000);
    };

    return (
      <div className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-center text-slate-900 mb-12">Contact Us</h2>
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <h3 className="text-2xl font-semibold text-slate-900 mb-6">Get In Touch</h3>
              <div className="space-y-4 text-gray-600">
                <p><strong>Phone:</strong> {business.phone}</p>
                <p><strong>Email:</strong> {business.email}</p>
                <p><strong>Address:</strong> {business.address}</p>
              </div>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              {submitted && (
                <div className="bg-green-100 text-green-700 p-4 rounded-lg">
                  Thank you! We'll be in touch soon.
                </div>
              )}
              <input type="text" placeholder="Your Name" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none" required />
              <input type="email" placeholder="Email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none" required />
              <input type="tel" placeholder="Phone" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none" />
              <textarea placeholder="How can we help?" value={formData.message} onChange={(e) => setFormData({...formData, message: e.target.value})} rows={4} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none" required />
              <button type="submit" className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition">
                Send Message
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  };

  const Footer = () => (
    <footer className="bg-slate-900 text-gray-300 py-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h3 className="text-xl font-bold text-white mb-4">{business.name}</h3>
        <p className="text-gray-400 mb-4">{business.tagline}</p>
        <p className="text-sm text-gray-500">&copy; 2026 {business.name}. All rights reserved.</p>
        <p className="mt-2 text-sm text-gray-600">Powered by Claude Opus 4.5 | Built with Faibric</p>
      </div>
    </footer>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      {currentView === "home" && <><HeroSection /><ServicesSection /><AboutSection /></>}
      {currentView === "services" && <ServicesSection />}
      {currentView === "about" && <AboutSection />}
      {currentView === "contact" && <ContactSection />}
      <Footer />
    </div>
  );
};

export default App;'''
    },
    {
        "name": "Fitness Studio",
        "description": "Gym, yoga studio, or fitness center website",
        "keywords": ["fitness", "gym", "yoga", "workout", "training", "exercise", "health", "wellness", "crossfit", "pilates"],
        "tags": ["fitness", "health", "business"],
        "code": '''// Golden Template: Fitness Studio
const App = () => {
  const [currentView, setCurrentView] = React.useState("home");

  const studio = {
    name: "{{BUSINESS_NAME}}",
    tagline: "{{TAGLINE}}",
    phone: "(555) 246-8135",
    address: "789 Fitness Blvd, City, State 12345"
  };

  const classes = [
    { id: 1, name: "HIIT Training", time: "6:00 AM", duration: "45 min", instructor: "Mike", level: "Advanced" },
    { id: 2, name: "Yoga Flow", time: "8:00 AM", duration: "60 min", instructor: "Sarah", level: "All Levels" },
    { id: 3, name: "Strength Training", time: "10:00 AM", duration: "50 min", instructor: "Jake", level: "Intermediate" },
    { id: 4, name: "Spin Class", time: "12:00 PM", duration: "45 min", instructor: "Emma", level: "All Levels" },
    { id: 5, name: "Boxing", time: "5:00 PM", duration: "60 min", instructor: "Chris", level: "Beginner" },
    { id: 6, name: "Pilates", time: "7:00 PM", duration: "55 min", instructor: "Lisa", level: "All Levels" }
  ];

  const plans = [
    { id: 1, name: "Drop-In", price: "$25", period: "per class", features: ["Single class access", "Towel service", "Locker use"] },
    { id: 2, name: "Monthly", price: "$99", period: "per month", features: ["Unlimited classes", "Free towels", "Locker included", "1 guest pass"], popular: true },
    { id: 3, name: "Annual", price: "$79", period: "per month", features: ["Unlimited classes", "Free towels", "Premium locker", "4 guest passes", "Free merchandise"] }
  ];

  const Navigation = () => (
    <nav className="bg-gradient-to-r from-emerald-600 to-teal-600 shadow-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <span className="text-2xl font-bold text-white">{studio.name}</span>
          <div className="flex space-x-1">
            {["home", "classes", "pricing", "contact"].map(view => (
              <button key={view} onClick={() => setCurrentView(view)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${currentView === view ? "bg-white text-emerald-600" : "text-white hover:bg-emerald-500"}`}>
                {view.charAt(0).toUpperCase() + view.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );

  const HeroSection = () => (
    <div className="bg-gradient-to-br from-emerald-600 via-teal-600 to-cyan-600 text-white py-24">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6">{studio.name}</h1>
        <p className="text-xl md:text-2xl text-emerald-100 mb-8">{studio.tagline}</p>
        <div className="flex justify-center gap-4">
          <button onClick={() => setCurrentView("pricing")} className="bg-white text-emerald-600 px-8 py-3 rounded-full font-semibold hover:bg-emerald-100 transition">
            Start Free Trial
          </button>
          <button onClick={() => setCurrentView("classes")} className="border-2 border-white px-8 py-3 rounded-full font-semibold hover:bg-white hover:text-emerald-600 transition">
            View Schedule
          </button>
        </div>
      </div>
    </div>
  );

  const ClassesSection = () => (
    <div className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-4xl font-bold text-center text-gray-900 mb-12">Class Schedule</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {classes.map(cls => (
            <div key={cls.id} className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition border-l-4 border-emerald-500">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-xl font-semibold text-gray-900">{cls.name}</h3>
                <span className="bg-emerald-100 text-emerald-700 text-xs px-2 py-1 rounded-full">{cls.level}</span>
              </div>
              <p className="text-2xl font-bold text-emerald-600 mb-2">{cls.time}</p>
              <p className="text-gray-600">{cls.duration} with {cls.instructor}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const PricingSection = () => (
    <div className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-4xl font-bold text-center text-gray-900 mb-12">Membership Plans</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {plans.map(plan => (
            <div key={plan.id} className={`rounded-2xl p-8 ${plan.popular ? "bg-emerald-600 text-white shadow-2xl scale-105" : "bg-gray-50 text-gray-900 shadow-lg"}`}>
              {plan.popular && <span className="bg-yellow-400 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full">MOST POPULAR</span>}
              <h3 className="text-2xl font-bold mt-4">{plan.name}</h3>
              <div className="my-6">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className={plan.popular ? "text-emerald-100" : "text-gray-500"}>/{plan.period}</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-center">
                    <span className="mr-2">&#10003;</span> {f}
                  </li>
                ))}
              </ul>
              <button className={`w-full py-3 rounded-lg font-semibold transition ${plan.popular ? "bg-white text-emerald-600 hover:bg-emerald-100" : "bg-emerald-600 text-white hover:bg-emerald-700"}`}>
                Get Started
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const ContactSection = () => {
    const [formData, setFormData] = React.useState({ name: "", email: "", phone: "", goal: "" });
    const [submitted, setSubmitted] = React.useState(false);
    const handleSubmit = (e) => { e.preventDefault(); setSubmitted(true); setTimeout(() => setSubmitted(false), 3000); };

    return (
      <div className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-center text-gray-900 mb-12">Start Your Journey</h2>
          <div className="bg-white rounded-2xl shadow-xl p-8">
            {submitted && <div className="bg-green-100 text-green-700 p-4 rounded-lg mb-6">Thanks! We'll contact you about your free trial.</div>}
            <form onSubmit={handleSubmit} className="grid md:grid-cols-2 gap-6">
              <input type="text" placeholder="Name" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none" required />
              <input type="email" placeholder="Email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none" required />
              <input type="tel" placeholder="Phone" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
              <select value={formData.goal} onChange={(e) => setFormData({...formData, goal: e.target.value})} className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none">
                <option value="">Fitness Goal</option>
                <option value="weight-loss">Weight Loss</option>
                <option value="muscle">Build Muscle</option>
                <option value="flexibility">Flexibility</option>
                <option value="general">General Fitness</option>
              </select>
              <button type="submit" className="md:col-span-2 bg-emerald-600 text-white py-3 rounded-lg font-semibold hover:bg-emerald-700 transition">
                Claim Free Trial
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  };

  const Footer = () => (
    <footer className="bg-gray-900 text-gray-300 py-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <h3 className="text-xl font-bold text-white mb-4">{studio.name}</h3>
        <p className="text-gray-400 mb-2">{studio.address}</p>
        <p className="text-gray-400 mb-4">{studio.phone}</p>
        <p className="text-sm text-gray-500">&copy; 2026 {studio.name}. All rights reserved.</p>
        <p className="mt-2 text-sm text-gray-600">Powered by Claude Opus 4.5 | Built with Faibric</p>
      </div>
    </footer>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      {currentView === "home" && <><HeroSection /><ClassesSection /><PricingSection /></>}
      {currentView === "classes" && <ClassesSection />}
      {currentView === "pricing" && <PricingSection />}
      {currentView === "contact" && <ContactSection />}
      <Footer />
    </div>
  );
};

export default App;'''
    },
]


class Command(BaseCommand):
    help = 'Create golden templates for instant app serving'

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for template_data in GOLDEN_TEMPLATES:
            item, was_created = LibraryItem.objects.update_or_create(
                name=template_data["name"],
                item_type="template",
                defaults={
                    "description": template_data["description"],
                    "code": template_data["code"],
                    "keywords": template_data["keywords"],
                    "tags": template_data["tags"],
                    "quality_score": 0.95,
                    "is_active": True,
                    "is_approved": True,
                    "is_public": True,
                    "needs_review": False,
                    "created_by": "admin",
                    "source": "golden",
                }
            )

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {template_data['name']}"))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f"Updated: {template_data['name']}"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! Created: {created}, Updated: {updated}"))
