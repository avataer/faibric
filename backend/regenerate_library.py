#!/usr/bin/env python3
"""
Regenerate the Faibric Component Library

This script:
1. Clears all existing corrupted components
2. Generates new, high-quality components for each standard type
3. Each component is a proper React component with real content

Run with: python manage.py shell < regenerate_library.py
Or: python regenerate_library.py (from backend directory with Django configured)
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.code_library.models import LibraryItem

print("=" * 60)
print("REGENERATING FAIBRIC COMPONENT LIBRARY")
print("=" * 60)

# Step 1: Count and clear existing components
existing_count = LibraryItem.objects.count()
print(f"\n[1] Clearing {existing_count} existing components...")

LibraryItem.objects.all().delete()
print(f"    Cleared!")

# Step 2: Define high-quality component templates
# These are REAL components with actual content, not placeholders

COMPONENTS = {
    # Navigation Components
    "navigation_header": {
        "name": "NavigationHeader",
        "description": "A responsive navigation header with logo and menu items",
        "code": '''
const NavigationHeader = ({ currentView, onNavigate, brandName = "Brand" }) => {
  const navItems = [
    { id: "home", label: "Home" },
    { id: "services", label: "Services" },
    { id: "about", label: "About" },
    { id: "contact", label: "Contact" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <nav className="bg-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <span className="text-2xl font-bold text-blue-600">{brandName}</span>
          </div>
          <div className="flex items-center space-x-4">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === item.id
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-600 hover:text-blue-600 hover:bg-gray-50"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};
''',
        "keywords": ["navigation", "header", "navbar", "menu"],
        "tags": ["navigation", "header"],
    },

    # Hero Components
    "hero_gradient": {
        "name": "HeroGradient",
        "description": "A hero section with gradient background and call-to-action",
        "code": '''
const HeroGradient = ({ 
  title = "Welcome to Our Service",
  subtitle = "We provide professional solutions tailored to your needs",
  ctaText = "Get Started",
  onCtaClick
}) => {
  return (
    <section className="relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white">
      <div className="absolute inset-0 bg-black opacity-10"></div>
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
        <div className="text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight mb-6">
            {title}
          </h1>
          <p className="text-xl md:text-2xl text-blue-100 max-w-3xl mx-auto mb-10">
            {subtitle}
          </p>
          <button
            onClick={onCtaClick}
            className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-lg bg-white text-blue-600 hover:bg-blue-50 transition-all transform hover:scale-105 shadow-xl"
          >
            {ctaText}
            <svg className="ml-2 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>
      <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent"></div>
    </section>
  );
};
''',
        "keywords": ["hero", "gradient", "landing", "cta", "banner"],
        "tags": ["hero", "gradient"],
    },

    # Services Components
    "services_grid": {
        "name": "ServicesGrid",
        "description": "A grid of service cards with icons and descriptions",
        "code": '''
const ServicesGrid = ({ services }) => {
  const defaultServices = [
    {
      title: "Consultation",
      description: "Expert advice tailored to your specific needs and goals",
      icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
    },
    {
      title: "Custom Solutions",
      description: "Personalized strategies designed for your unique situation",
      icon: "M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"
    },
    {
      title: "Ongoing Support",
      description: "Continuous assistance to ensure your continued success",
      icon: "M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    },
    {
      title: "Expert Advice",
      description: "Professional guidance from experienced specialists",
      icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
    }
  ];

  const items = services || defaultServices;

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Our Services</h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Comprehensive solutions to meet all your needs
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {items.map((service, index) => (
            <div
              key={index}
              className="bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow p-6 text-center"
            >
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={service.icon} />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{service.title}</h3>
              <p className="text-gray-600">{service.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
        "keywords": ["services", "grid", "cards", "features"],
        "tags": ["services", "grid"],
    },

    # About Components
    "about_section": {
        "name": "AboutSection",
        "description": "An about section with company info and mission statement",
        "code": '''
const AboutSection = ({ 
  title = "About Us",
  mission = "Our mission is to deliver exceptional service and build lasting relationships with our clients.",
  description = "We are a team of dedicated professionals with years of experience in our field. Our commitment to excellence drives everything we do.",
  stats
}) => {
  const defaultStats = [
    { value: "10+", label: "Years Experience" },
    { value: "500+", label: "Happy Clients" },
    { value: "98%", label: "Satisfaction Rate" },
    { value: "24/7", label: "Support" }
  ];

  const displayStats = stats || defaultStats;

  return (
    <section className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">{title}</h2>
            <p className="text-lg text-gray-600 mb-6">{description}</p>
            <p className="text-lg text-blue-600 font-medium italic">{mission}</p>
          </div>
          <div className="grid grid-cols-2 gap-6">
            {displayStats.map((stat, index) => (
              <div key={index} className="bg-blue-50 rounded-lg p-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-2">{stat.value}</div>
                <div className="text-gray-600">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
''',
        "keywords": ["about", "company", "mission", "stats"],
        "tags": ["about", "section"],
    },

    # Contact Components
    "contact_form": {
        "name": "ContactForm",
        "description": "A contact form with name, email, and message fields",
        "code": '''
const ContactForm = ({ onSubmit, title = "Contact Us" }) => {
  const [formData, setFormData] = React.useState({
    name: "",
    email: "",
    phone: "",
    message: ""
  });
  const [submitted, setSubmitted] = React.useState(false);
  const [errors, setErrors] = React.useState({});

  const validate = () => {
    const newErrors = {};
    if (!formData.name.trim()) newErrors.name = "Name is required";
    if (!formData.email.trim()) newErrors.email = "Email is required";
    else if (!/\\S+@\\S+\\.\\S+/.test(formData.email)) newErrors.email = "Email is invalid";
    if (!formData.message.trim()) newErrors.message = "Message is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      if (onSubmit) onSubmit(formData);
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setFormData({ name: "", email: "", phone: "", message: "" });
      }, 3000);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: null }));
  };

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">{title}</h2>
          <p className="text-gray-600">We would love to hear from you. Send us a message!</p>
        </div>

        {submitted && (
          <div className="mb-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
            Thank you for your message! We will get back to you soon.
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.name ? "border-red-500" : "border-gray-300"
                }`}
                placeholder="Your name"
              />
              {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.email ? "border-red-500" : "border-gray-300"
                }`}
                placeholder="your@email.com"
              />
              {errors.email && <p className="mt-1 text-sm text-red-500">{errors.email}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone (optional)</label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Your phone number"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Message *</label>
              <textarea
                name="message"
                value={formData.message}
                onChange={handleChange}
                rows={5}
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.message ? "border-red-500" : "border-gray-300"
                }`}
                placeholder="How can we help you?"
              />
              {errors.message && <p className="mt-1 text-sm text-red-500">{errors.message}</p>}
            </div>

            <button
              type="submit"
              className="w-full py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              Send Message
            </button>
          </div>
        </form>
      </div>
    </section>
  );
};
''',
        "keywords": ["contact", "form", "email", "message"],
        "tags": ["contact", "form"],
    },

    # Footer Components
    "footer_simple": {
        "name": "FooterSimple",
        "description": "A simple footer with links and copyright",
        "code": '''
const FooterSimple = ({ brandName = "Brand", year = new Date().getFullYear() }) => {
  const links = [
    { label: "Home", href: "#" },
    { label: "About", href: "#" },
    { label: "Services", href: "#" },
    { label: "Contact", href: "#" },
    { label: "Privacy Policy", href: "#" },
  ];

  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid md:grid-cols-3 gap-8">
          <div>
            <span className="text-2xl font-bold text-blue-400">{brandName}</span>
            <p className="mt-4 text-gray-400">
              Providing quality services since {year - 10}. We are committed to excellence.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              {links.map((link, index) => (
                <li key={index}>
                  <a href={link.href} className="text-gray-400 hover:text-white transition-colors">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">Contact</h3>
            <ul className="space-y-2 text-gray-400">
              <li>Email: contact@example.com</li>
              <li>Phone: (555) 123-4567</li>
              <li>Address: 123 Main St, City</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
          <p>&copy; {year} {brandName}. All rights reserved. Built with Faibric.</p>
        </div>
      </div>
    </footer>
  );
};
''',
        "keywords": ["footer", "copyright", "links"],
        "tags": ["footer", "simple"],
    },

    # Settings Components
    "settings_view": {
        "name": "SettingsView",
        "description": "A settings page with common configuration options",
        "code": '''
const SettingsView = () => {
  const [settings, setSettings] = React.useState({
    notifications: true,
    darkMode: false,
    language: "en",
    refreshInterval: "30"
  });

  const handleToggle = (key) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <section className="py-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>
        
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          {/* Notifications */}
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">Notifications</h3>
              <p className="text-sm text-gray-500">Receive updates and alerts</p>
            </div>
            <button
              onClick={() => handleToggle("notifications")}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.notifications ? "bg-blue-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                  settings.notifications ? "translate-x-6" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Dark Mode */}
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">Dark Mode</h3>
              <p className="text-sm text-gray-500">Use dark theme</p>
            </div>
            <button
              onClick={() => handleToggle("darkMode")}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.darkMode ? "bg-blue-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                  settings.darkMode ? "translate-x-6" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Language */}
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">Language</h3>
              <p className="text-sm text-gray-500">Select your preferred language</p>
            </div>
            <select
              value={settings.language}
              onChange={(e) => handleChange("language", e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
            </select>
          </div>

          {/* Refresh Interval */}
          <div className="p-6 flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">Auto Refresh</h3>
              <p className="text-sm text-gray-500">Data refresh interval</p>
            </div>
            <select
              value={settings.refreshInterval}
              onChange={(e) => handleChange("refreshInterval", e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="10">10 seconds</option>
              <option value="30">30 seconds</option>
              <option value="60">1 minute</option>
              <option value="300">5 minutes</option>
            </select>
          </div>
        </div>

        <p className="mt-4 text-sm text-gray-500 text-center">
          Settings are saved automatically
        </p>
      </div>
    </section>
  );
};
''',
        "keywords": ["settings", "preferences", "config", "options"],
        "tags": ["settings", "view"],
    },

    # Dashboard Components
    "dashboard_stats": {
        "name": "DashboardStats",
        "description": "A dashboard with stats cards and overview",
        "code": '''
const DashboardStats = ({ data, loading = false }) => {
  const defaultStats = [
    { label: "Total Users", value: "1,234", change: "+12%", positive: true },
    { label: "Revenue", value: "$45,678", change: "+8%", positive: true },
    { label: "Orders", value: "567", change: "-3%", positive: false },
    { label: "Conversion", value: "3.2%", change: "+0.5%", positive: true }
  ];

  const stats = data || defaultStats;

  if (loading) {
    return (
      <div className="grid md:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl shadow-md p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <section className="py-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard Overview</h2>
      <div className="grid md:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow">
            <p className="text-sm font-medium text-gray-500 mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900 mb-2">{stat.value}</p>
            <span className={`inline-flex items-center text-sm font-medium ${
              stat.positive ? "text-green-600" : "text-red-600"
            }`}>
              {stat.positive ? (
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
              {stat.change}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
};
''',
        "keywords": ["dashboard", "stats", "analytics", "overview", "cards"],
        "tags": ["dashboard", "stats"],
    },

    # Pricing Components
    "pricing_table": {
        "name": "PricingTable",
        "description": "A pricing table with multiple tiers",
        "code": '''
const PricingTable = ({ plans, onSelectPlan }) => {
  const defaultPlans = [
    {
      name: "Starter",
      price: "29",
      period: "month",
      description: "Perfect for individuals and small projects",
      features: ["5 Projects", "Basic Support", "1GB Storage", "Email Notifications"],
      popular: false
    },
    {
      name: "Professional",
      price: "79",
      period: "month",
      description: "Best for growing businesses",
      features: ["Unlimited Projects", "Priority Support", "10GB Storage", "Advanced Analytics", "Custom Domain"],
      popular: true
    },
    {
      name: "Enterprise",
      price: "199",
      period: "month",
      description: "For large organizations",
      features: ["Everything in Pro", "Dedicated Support", "Unlimited Storage", "SSO Integration", "SLA Guarantee", "Custom Features"],
      popular: false
    }
  ];

  const displayPlans = plans || defaultPlans;

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Simple, Transparent Pricing</h2>
          <p className="text-lg text-gray-600">Choose the plan that works for you</p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8">
          {displayPlans.map((plan, index) => (
            <div
              key={index}
              className={`relative bg-white rounded-2xl shadow-lg overflow-hidden ${
                plan.popular ? "ring-2 ring-blue-600" : ""
              }`}
            >
              {plan.popular && (
                <div className="absolute top-0 right-0 bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-bl-lg">
                  Most Popular
                </div>
              )}
              <div className="p-8">
                <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                <p className="text-gray-500 mb-6">{plan.description}</p>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
                  <span className="text-gray-500">/{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-center text-gray-600">
                      <svg className="w-5 h-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => onSelectPlan && onSelectPlan(plan)}
                  className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                    plan.popular
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                  }`}
                >
                  Get Started
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
        "keywords": ["pricing", "plans", "subscription", "tiers"],
        "tags": ["pricing", "table"],
    },

    # Testimonials Components
    "testimonials_carousel": {
        "name": "TestimonialsCarousel",
        "description": "A testimonials section with customer reviews",
        "code": '''
const TestimonialsCarousel = ({ testimonials }) => {
  const [activeIndex, setActiveIndex] = React.useState(0);

  const defaultTestimonials = [
    {
      name: "Sarah Johnson",
      role: "CEO, TechStart",
      content: "Working with this team has been an absolute pleasure. They delivered beyond our expectations and the results speak for themselves.",
      rating: 5
    },
    {
      name: "Michael Chen",
      role: "Founder, GrowthLab",
      content: "The level of professionalism and attention to detail is outstanding. I highly recommend their services to anyone looking for quality work.",
      rating: 5
    },
    {
      name: "Emily Davis",
      role: "Marketing Director",
      content: "They transformed our vision into reality. The project was delivered on time and the communication throughout was excellent.",
      rating: 5
    }
  ];

  const items = testimonials || defaultTestimonials;

  const nextSlide = () => {
    setActiveIndex((prev) => (prev + 1) % items.length);
  };

  const prevSlide = () => {
    setActiveIndex((prev) => (prev - 1 + items.length) % items.length);
  };

  return (
    <section className="py-16 bg-blue-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">What Our Clients Say</h2>
        </div>

        <div className="relative bg-white rounded-2xl shadow-xl p-8 md:p-12">
          <svg className="absolute top-6 left-6 w-12 h-12 text-blue-100" fill="currentColor" viewBox="0 0 32 32">
            <path d="M10 8c-3.3 0-6 2.7-6 6v10h10V14H8c0-1.1.9-2 2-2V8zm14 0c-3.3 0-6 2.7-6 6v10h10V14h-6c0-1.1.9-2 2-2V8z" />
          </svg>

          <div className="text-center">
            <p className="text-xl text-gray-700 mb-8 italic">
              "{items[activeIndex].content}"
            </p>
            <div className="flex justify-center mb-4">
              {[...Array(items[activeIndex].rating)].map((_, i) => (
                <svg key={i} className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>
            <p className="font-semibold text-gray-900">{items[activeIndex].name}</p>
            <p className="text-gray-500">{items[activeIndex].role}</p>
          </div>

          <div className="flex justify-center mt-8 space-x-4">
            <button
              onClick={prevSlide}
              className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex items-center space-x-2">
              {items.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setActiveIndex(index)}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    index === activeIndex ? "bg-blue-600" : "bg-gray-300"
                  }`}
                />
              ))}
            </div>
            <button
              onClick={nextSlide}
              className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
''',
        "keywords": ["testimonials", "reviews", "carousel", "clients"],
        "tags": ["testimonials", "carousel"],
    },
}

# Step 3: Create components in database
print(f"\n[2] Creating {len(COMPONENTS)} high-quality components...")

for key, comp in COMPONENTS.items():
    parts = key.split("_", 1)
    comp_type = parts[0]
    variant = parts[1] if len(parts) > 1 else "default"
    
    item = LibraryItem.objects.create(
        name=comp["name"],
        slug=key,
        description=comp["description"],
        usage_example=f'<{comp["name"]} />',
        documentation=f"## {comp['name']}\n\n{comp['description']}\n\n### Usage\n```tsx\n<{comp['name']} />\n```",
        item_type="component",
        language="tsx",
        code=comp["code"].strip(),
        keywords=comp["keywords"],
        tags=comp["tags"],
        quality_score=0.9,  # High quality
        is_active=True,
        is_public=True,
        is_deprecated=False,
        needs_review=False,  # Pre-approved
        created_by="admin"
    )
    print(f"    Created: {comp['name']} ({item.id})")

# Summary
final_count = LibraryItem.objects.count()
print(f"\n[3] COMPLETE!")
print(f"    Components created: {final_count}")
print(f"    Component types: navigation, hero, services, about, contact, footer, settings, dashboard, pricing, testimonials")

print("\n" + "=" * 60)
print("Library regeneration complete!")
print("=" * 60)
