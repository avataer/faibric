"""
Template Registry - All golden templates in one place.

Each template has:
- code: The JSX template with placeholders
- schema: JSON schema for required data
- category: Component type (hero, navigation, etc.)
- variant: Style variant (centered, split, etc.)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class GoldenTemplate:
    """A pre-validated, battle-tested component template."""
    name: str
    category: str
    variant: str
    code: str
    schema: Dict
    description: str = ""

    def render(self, data: Dict) -> str:
        """Render template with provided data."""
        code = self.code

        # Simple placeholder replacement
        # Format: {{key}} or {{key.subkey}}
        for key, value in data.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    placeholder = f"{{{{{key}.{subkey}}}}}"
                    code = code.replace(placeholder, str(subvalue))
            elif isinstance(value, list):
                # Lists are handled specially in template code
                placeholder = f"{{{{@{key}}}}}"
                # Convert to JSON for safe injection
                code = code.replace(placeholder, json.dumps(value))
            else:
                placeholder = f"{{{{{key}}}}}"
                code = code.replace(placeholder, str(value))

        return code


# =============================================================================
# HERO TEMPLATES
# =============================================================================

HERO_CENTERED = GoldenTemplate(
    name="hero_centered",
    category="hero",
    variant="centered",
    description="Centered hero with headline, subheadline, and CTA button",
    schema={
        "type": "object",
        "required": ["headline", "subheadline", "cta_text"],
        "properties": {
            "headline": {"type": "string", "description": "Main headline (5-10 words)"},
            "subheadline": {"type": "string", "description": "Supporting text (10-20 words)"},
            "cta_text": {"type": "string", "description": "Button text (2-4 words)"},
            "background_seed": {"type": "string", "description": "Keyword for Picsum image seed"},
        }
    },
    code='''
const HeroSection = ({ onNavigate }) => {
  return (
    <section
      className="min-h-screen bg-cover bg-center relative flex items-center justify-center"
      style={{backgroundImage: "url('https://picsum.photos/seed/{{background_seed}}/1920/1080')"}}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/50 to-transparent"></div>
      <div className="relative z-10 text-center text-white px-4 max-w-4xl">
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          {{headline}}
        </h1>
        <p className="text-xl md:text-2xl mb-8 opacity-90">
          {{subheadline}}
        </p>
        <button
          onClick={() => onNavigate && onNavigate("contact")}
          className="px-8 py-4 bg-white text-gray-900 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-all duration-300 shadow-xl hover:shadow-2xl transform hover:scale-105"
        >
          {{cta_text}}
        </button>
      </div>
    </section>
  );
};
'''
)

HERO_SPLIT = GoldenTemplate(
    name="hero_split",
    category="hero",
    variant="split",
    description="Split hero with text on left, image on right",
    schema={
        "type": "object",
        "required": ["headline", "subheadline", "cta_text"],
        "properties": {
            "headline": {"type": "string"},
            "subheadline": {"type": "string"},
            "cta_text": {"type": "string"},
            "image_seed": {"type": "string"},
        }
    },
    code='''
const HeroSection = ({ onNavigate }) => {
  return (
    <section className="min-h-screen flex flex-col md:flex-row">
      <div className="flex-1 flex items-center justify-center p-8 md:p-16 bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="max-w-xl">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6 leading-tight">
            {{headline}}
          </h1>
          <p className="text-lg text-gray-300 mb-8">
            {{subheadline}}
          </p>
          <button
            onClick={() => onNavigate && onNavigate("contact")}
            className="px-8 py-4 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-all duration-300 shadow-lg"
          >
            {{cta_text}}
          </button>
        </div>
      </div>
      <div
        className="flex-1 bg-cover bg-center min-h-[400px]"
        style={{backgroundImage: "url('https://picsum.photos/seed/{{image_seed}}/1200/900')"}}
      ></div>
    </section>
  );
};
'''
)


# =============================================================================
# NAVIGATION TEMPLATES
# =============================================================================

NAVIGATION_SIMPLE = GoldenTemplate(
    name="navigation_simple",
    category="navigation",
    variant="simple",
    description="Simple horizontal navigation with logo and links",
    schema={
        "type": "object",
        "required": ["business_name", "nav_items"],
        "properties": {
            "business_name": {"type": "string"},
            "nav_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"}
                    }
                }
            }
        }
    },
    code='''
const Navigation = ({ currentView, onNavigate }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const navItems = {{@nav_items}};

  return (
    <nav className="bg-white shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <span className="text-xl font-bold text-gray-900">{{business_name}}</span>

          <div className="hidden md:flex items-center gap-8">
            {(navItems || []).map(item => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`text-sm font-medium transition-colors ${
                  currentView === item.id
                    ? "text-indigo-600"
                    : "text-gray-600 hover:text-indigo-600"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <button
            className="md:hidden p-2"
            onClick={() => setIsOpen(!isOpen)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>

        {isOpen && (
          <div className="md:hidden pb-4">
            {(navItems || []).map(item => (
              <button
                key={item.id}
                onClick={() => { onNavigate(item.id); setIsOpen(false); }}
                className={`block w-full text-left py-2 px-4 ${
                  currentView === item.id ? "text-indigo-600 bg-indigo-50" : "text-gray-600"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
};
'''
)


# =============================================================================
# FEATURES/SERVICES TEMPLATES
# =============================================================================

FEATURES_GRID = GoldenTemplate(
    name="features_grid",
    category="features",
    variant="grid",
    description="Grid of feature cards with icons",
    schema={
        "type": "object",
        "required": ["section_title", "features"],
        "properties": {
            "section_title": {"type": "string"},
            "section_subtitle": {"type": "string"},
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "icon_letter": {"type": "string", "description": "Single letter for icon"}
                    }
                }
            }
        }
    },
    code='''
const FeaturesSection = () => {
  const features = {{@features}};

  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">{{section_title}}</h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">{{section_subtitle}}</p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {(features || []).map((feature, index) => (
            <div
              key={index}
              className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center mb-6">
                <span className="text-2xl font-bold text-white">{feature.icon_letter || (index + 1)}</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">{feature.title}</h3>
              <p className="text-gray-600 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
'''
)

SERVICES_LIST = GoldenTemplate(
    name="services_list",
    category="services",
    variant="list",
    description="List of services with descriptions",
    schema={
        "type": "object",
        "required": ["section_title", "services"],
        "properties": {
            "section_title": {"type": "string"},
            "services": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "price": {"type": "string", "description": "Optional price or 'Contact us'"}
                    }
                }
            }
        }
    },
    code='''
const ServicesSection = () => {
  const services = {{@services}};

  return (
    <section className="py-20 px-4">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-4xl font-bold text-center text-gray-900 mb-16">{{section_title}}</h2>

        <div className="space-y-6">
          {(services || []).map((service, index) => (
            <div
              key={index}
              className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{service.name}</h3>
                  <p className="text-gray-600">{service.description}</p>
                </div>
                {service.price && (
                  <span className="text-lg font-semibold text-indigo-600 ml-4">{service.price}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
'''
)


# =============================================================================
# CONTACT TEMPLATES
# =============================================================================

CONTACT_SIMPLE = GoldenTemplate(
    name="contact_simple",
    category="contact",
    variant="simple",
    description="Simple contact form with name, email, message",
    schema={
        "type": "object",
        "required": ["section_title"],
        "properties": {
            "section_title": {"type": "string"},
            "section_subtitle": {"type": "string"},
            "submit_text": {"type": "string", "default": "Send Message"},
            "phone": {"type": "string"},
            "email": {"type": "string"},
            "address": {"type": "string"}
        }
    },
    code='''
const ContactSection = () => {
  const [formData, setFormData] = React.useState({ name: "", email: "", message: "" });
  const [submitted, setSubmitted] = React.useState(false);
  const [sending, setSending] = React.useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));

    console.log("Contact form submitted:", formData);
    setSubmitted(true);
    setSending(false);
    setFormData({ name: "", email: "", message: "" });

    setTimeout(() => setSubmitted(false), 5000);
  };

  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">{{section_title}}</h2>
          <p className="text-xl text-gray-600">{{section_subtitle}}</p>
        </div>

        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <form onSubmit={handleSubmit} className="space-y-6">
              {submitted && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
                  Thank you for your message. We will get back to you soon.
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
                <textarea
                  value={formData.message}
                  onChange={(e) => setFormData({...formData, message: e.target.value})}
                  rows="5"
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none"
                  required
                ></textarea>
              </div>

              <button
                type="submit"
                disabled={sending}
                className="w-full py-4 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-colors disabled:bg-gray-400"
              >
                {sending ? "Sending..." : "{{submit_text}}"}
              </button>
            </form>
          </div>

          <div className="space-y-8">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h3>
              <div className="space-y-4 text-gray-600">
                <p className="flex items-center gap-3">
                  <span className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                  </span>
                  {{phone}}
                </p>
                <p className="flex items-center gap-3">
                  <span className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </span>
                  {{email}}
                </p>
                <p className="flex items-center gap-3">
                  <span className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </span>
                  {{address}}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
'''
)


# =============================================================================
# ABOUT TEMPLATES
# =============================================================================

ABOUT_SIMPLE = GoldenTemplate(
    name="about_simple",
    category="about",
    variant="simple",
    description="Simple about section with text and optional image",
    schema={
        "type": "object",
        "required": ["section_title", "paragraphs"],
        "properties": {
            "section_title": {"type": "string"},
            "paragraphs": {
                "type": "array",
                "items": {"type": "string"}
            },
            "image_seed": {"type": "string"}
        }
    },
    code='''
const AboutSection = () => {
  const paragraphs = {{@paragraphs}};

  return (
    <section className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-4xl font-bold text-gray-900 mb-8">{{section_title}}</h2>
            <div className="space-y-4 text-lg text-gray-600 leading-relaxed">
              {(paragraphs || []).map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </div>
          <div className="relative">
            <div className="absolute -inset-4 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl opacity-20 blur-xl"></div>
            <img
              src="https://picsum.photos/seed/{{image_seed}}/800/600"
              alt="About us"
              className="relative rounded-2xl shadow-xl w-full"
            />
          </div>
        </div>
      </div>
    </section>
  );
};
'''
)


# =============================================================================
# TESTIMONIALS TEMPLATES
# =============================================================================

TESTIMONIALS_CARDS = GoldenTemplate(
    name="testimonials_cards",
    category="testimonials",
    variant="cards",
    description="Grid of testimonial cards with quotes",
    schema={
        "type": "object",
        "required": ["section_title", "testimonials"],
        "properties": {
            "section_title": {"type": "string"},
            "testimonials": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quote": {"type": "string"},
                        "name": {"type": "string"},
                        "role": {"type": "string"}
                    }
                }
            }
        }
    },
    code='''
const TestimonialsSection = () => {
  const testimonials = {{@testimonials}};

  return (
    <section className="py-20 px-4 bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-4xl font-bold text-center text-white mb-16">{{section_title}}</h2>

        <div className="grid md:grid-cols-3 gap-8">
          {(testimonials || []).map((testimonial, index) => (
            <div
              key={index}
              className="bg-white/10 backdrop-blur-sm p-8 rounded-2xl border border-white/20"
            >
              <div className="text-4xl text-indigo-400 mb-4">"</div>
              <p className="text-gray-300 mb-6 leading-relaxed">{testimonial.quote}</p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">{testimonial.name?.charAt(0) || "?"}</span>
                </div>
                <div>
                  <p className="text-white font-semibold">{testimonial.name}</p>
                  <p className="text-gray-400 text-sm">{testimonial.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
'''
)


# =============================================================================
# FOOTER TEMPLATES
# =============================================================================

FOOTER_SIMPLE = GoldenTemplate(
    name="footer_simple",
    category="footer",
    variant="simple",
    description="Simple footer with copyright and links",
    schema={
        "type": "object",
        "required": ["business_name"],
        "properties": {
            "business_name": {"type": "string"},
            "tagline": {"type": "string"},
            "year": {"type": "string", "default": "2024"}
        }
    },
    code='''
const FooterSection = () => {
  return (
    <footer className="bg-gray-900 text-white py-12">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center">
          <h3 className="text-2xl font-bold mb-2">{{business_name}}</h3>
          <p className="text-gray-400 mb-6">{{tagline}}</p>
          <div className="border-t border-gray-800 pt-6">
            <p className="text-gray-500 text-sm">
              {{year}} {{business_name}}. All rights reserved.
            </p>
            <p className="text-gray-600 text-xs mt-2">Built with Faibric</p>
          </div>
        </div>
      </div>
    </footer>
  );
};
'''
)


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

TEMPLATE_REGISTRY: Dict[str, Dict[str, GoldenTemplate]] = {
    "hero": {
        "centered": HERO_CENTERED,
        "split": HERO_SPLIT,
    },
    "navigation": {
        "simple": NAVIGATION_SIMPLE,
    },
    "features": {
        "grid": FEATURES_GRID,
    },
    "services": {
        "list": SERVICES_LIST,
    },
    "contact": {
        "simple": CONTACT_SIMPLE,
    },
    "about": {
        "simple": ABOUT_SIMPLE,
    },
    "testimonials": {
        "cards": TESTIMONIALS_CARDS,
    },
    "footer": {
        "simple": FOOTER_SIMPLE,
    },
}


def get_template(category: str, variant: str = None) -> Optional[GoldenTemplate]:
    """Get a template by category and variant."""
    if category not in TEMPLATE_REGISTRY:
        return None

    variants = TEMPLATE_REGISTRY[category]

    if variant and variant in variants:
        return variants[variant]

    # Return first variant as default
    return next(iter(variants.values())) if variants else None


def list_templates() -> List[Dict]:
    """List all available templates."""
    result = []
    for category, variants in TEMPLATE_REGISTRY.items():
        for variant, template in variants.items():
            result.append({
                "name": template.name,
                "category": category,
                "variant": variant,
                "description": template.description,
                "schema": template.schema,
            })
    return result
