"""
Code Generator for Project Services
Generates JavaScript/React code for database, auth, payments, etc.
"""
from typing import Dict, List
from .feature_detector import RequiredFeatures


class ServiceCodeGenerator:
    """
    Generates React code snippets for project services.
    """
    
    def generate_all(self, features: RequiredFeatures, config: Dict) -> str:
        """
        Generate all required service code based on detected features.
        """
        code_blocks = []
        
        if features.needs_database or features.needs_auth:
            code_blocks.append(self._generate_supabase_init(config))
        
        if features.needs_auth:
            code_blocks.append(self._generate_auth_code(config, features.auth_providers))
        
        if features.needs_database:
            code_blocks.append(self._generate_database_code(config, features.database_tables))
        
        if features.needs_payments:
            code_blocks.append(self._generate_payment_code(config, features.payment_type))
        
        if features.needs_storage:
            code_blocks.append(self._generate_storage_code(config))
        
        return '\n\n'.join(code_blocks)
    
    def _generate_supabase_init(self, config: Dict) -> str:
        """Generate Supabase client initialization."""
        url = config.get('supabase_url', 'YOUR_SUPABASE_URL')
        key = config.get('supabase_anon_key', 'YOUR_SUPABASE_ANON_KEY')
        
        return f'''
// ═══════════════════════════════════════════════════════════════════════════════
// SUPABASE CLIENT
// ═══════════════════════════════════════════════════════════════════════════════
const SUPABASE_URL = "{url}";
const SUPABASE_ANON_KEY = "{key}";

// Load Supabase client from CDN
const supabaseScript = document.createElement("script");
supabaseScript.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";
document.head.appendChild(supabaseScript);

// Wait for Supabase to load
const waitForSupabase = () => new Promise((resolve) => {{
  const check = () => {{
    if (window.supabase) {{
      resolve(window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY));
    }} else {{
      setTimeout(check, 100);
    }}
  }};
  check();
}});

// Supabase client (initialized on first use)
let supabaseClient = null;
const getSupabase = async () => {{
  if (!supabaseClient) {{
    supabaseClient = await waitForSupabase();
  }}
  return supabaseClient;
}};
'''
    
    def _generate_auth_code(self, config: Dict, providers: List[str]) -> str:
        """Generate authentication code."""
        code = '''
// ═══════════════════════════════════════════════════════════════════════════════
// AUTHENTICATION
// ═══════════════════════════════════════════════════════════════════════════════

// Auth state
const [user, setUser] = React.useState(null);
const [authLoading, setAuthLoading] = React.useState(true);

// Check auth state on mount
React.useEffect(() => {
  const checkAuth = async () => {
    const supabase = await getSupabase();
    const { data: { user } } = await supabase.auth.getUser();
    setUser(user);
    setAuthLoading(false);
    
    // Listen for auth changes
    supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
    });
  };
  checkAuth();
}, []);

// Sign up with email/password
const signUp = async (email, password) => {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) throw error;
  return data;
};

// Sign in with email/password
const signIn = async (email, password) => {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
};

// Sign out
const signOut = async () => {
  const supabase = await getSupabase();
  await supabase.auth.signOut();
  setUser(null);
};
'''
        
        if 'magic_link' in providers:
            code += '''
// Sign in with magic link
const signInWithMagicLink = async (email) => {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.signInWithOtp({ 
    email,
    options: { emailRedirectTo: window.location.origin }
  });
  if (error) throw error;
  return data;
};
'''
        
        if 'google' in providers:
            code += '''
// Sign in with Google
const signInWithGoogle = async () => {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin }
  });
  if (error) throw error;
  return data;
};
'''
        
        if 'github' in providers:
            code += '''
// Sign in with GitHub
const signInWithGitHub = async () => {
  const supabase = await getSupabase();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "github",
    options: { redirectTo: window.location.origin }
  });
  if (error) throw error;
  return data;
};
'''
        
        code += '''
// Auth Form Component
const AuthForm = ({ onSuccess }) => {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [isSignUp, setIsSignUp] = React.useState(false);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    
    try {
      if (isSignUp) {
        await signUp(email, password);
        alert("Check your email for the confirmation link!");
      } else {
        await signIn(email, password);
        if (onSuccess) onSuccess();
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };
  
  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-6">{isSignUp ? "Create Account" : "Sign In"}</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
            required
            minLength={6}
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Loading..." : (isSignUp ? "Sign Up" : "Sign In")}
        </button>
      </form>
      
      <p className="mt-4 text-center text-sm text-gray-600">
        {isSignUp ? "Already have an account?" : "Don't have an account?"}
        <button 
          onClick={() => setIsSignUp(!isSignUp)}
          className="ml-1 text-blue-600 hover:underline"
        >
          {isSignUp ? "Sign In" : "Sign Up"}
        </button>
      </p>
    </div>
  );
};
'''
        return code
    
    def _generate_database_code(self, config: Dict, tables: List[str]) -> str:
        """Generate database CRUD operations."""
        code = '''
// ═══════════════════════════════════════════════════════════════════════════════
// DATABASE OPERATIONS
// ═══════════════════════════════════════════════════════════════════════════════

// Generic CRUD hook
const useTable = (tableName) => {
  const [items, setItems] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  
  const fetchAll = async () => {
    setLoading(true);
    try {
      const supabase = await getSupabase();
      const { data, error } = await supabase
        .from(tableName)
        .select("*")
        .order("created_at", { ascending: false });
      if (error) throw error;
      setItems(data || []);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };
  
  const create = async (item) => {
    try {
      const supabase = await getSupabase();
      const { data, error } = await supabase
        .from(tableName)
        .insert(item)
        .select();
      if (error) throw error;
      setItems([...(data || []), ...items]);
      return data?.[0];
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };
  
  const update = async (id, updates) => {
    try {
      const supabase = await getSupabase();
      const { data, error } = await supabase
        .from(tableName)
        .update(updates)
        .eq("id", id)
        .select();
      if (error) throw error;
      setItems(items.map(item => item.id === id ? { ...item, ...updates } : item));
      return data?.[0];
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };
  
  const remove = async (id) => {
    try {
      const supabase = await getSupabase();
      const { error } = await supabase
        .from(tableName)
        .delete()
        .eq("id", id);
      if (error) throw error;
      setItems(items.filter(item => item.id !== id));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };
  
  React.useEffect(() => {
    fetchAll();
  }, [tableName]);
  
  return { items, loading, error, fetchAll, create, update, remove };
};
'''
        
        # Generate specific hooks for each table
        for table in tables:
            singular = table.rstrip('s')
            code += f'''
// {table.title()} hook
const use{table.title()} = () => useTable("{table}");
'''
        
        return code
    
    def _generate_payment_code(self, config: Dict, payment_type: str) -> str:
        """Generate Stripe payment code."""
        publishable_key = config.get('stripe_publishable_key', 'pk_test_YOUR_KEY')
        
        code = f'''
// ═══════════════════════════════════════════════════════════════════════════════
// PAYMENTS (Stripe)
// ═══════════════════════════════════════════════════════════════════════════════

// Load Stripe.js
const stripeScript = document.createElement("script");
stripeScript.src = "https://js.stripe.com/v3/";
document.head.appendChild(stripeScript);

const STRIPE_PUBLISHABLE_KEY = "{publishable_key}";

// Get Stripe instance
let stripeInstance = null;
const getStripe = () => {{
  if (!stripeInstance && window.Stripe) {{
    stripeInstance = window.Stripe(STRIPE_PUBLISHABLE_KEY);
  }}
  return stripeInstance;
}};

// Redirect to Stripe Checkout
const checkout = async (priceId, mode = "{payment_type or 'payment'}") => {{
  const stripe = getStripe();
  if (!stripe) {{
    alert("Stripe is loading, please try again.");
    return;
  }}
  
  // In production, create checkout session on backend
  // For now, redirect directly (requires Stripe Dashboard setup)
  const {{ error }} = await stripe.redirectToCheckout({{
    lineItems: [{{ price: priceId, quantity: 1 }}],
    mode: mode === "subscription" ? "subscription" : "payment",
    successUrl: window.location.origin + "/success",
    cancelUrl: window.location.origin + "/cancel",
  }});
  
  if (error) {{
    console.error("Checkout error:", error);
    alert(error.message);
  }}
}};

// Checkout Button Component
const CheckoutButton = ({{ priceId, label = "Buy Now", className = "" }}) => (
  <button
    onClick={{() => checkout(priceId)}}
    className={{`px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium ${{className}}`}}
  >
    {{label}}
  </button>
);

// Pricing Card Component
const PricingCard = ({{ name, price, features = [], priceId, popular = false }}) => (
  <div className={{`p-6 rounded-xl border-2 ${{popular ? "border-indigo-500 shadow-xl" : "border-gray-200"}}`}}>
    {{popular && (
      <span className="px-3 py-1 text-xs font-semibold text-indigo-600 bg-indigo-100 rounded-full">
        Most Popular
      </span>
    )}}
    <h3 className="mt-4 text-xl font-bold">{{name}}</h3>
    <p className="mt-2 text-4xl font-bold">${{price}}<span className="text-lg text-gray-500">/mo</span></p>
    <ul className="mt-6 space-y-3">
      {{features.map((feature, i) => (
        <li key={{i}} className="flex items-center gap-2">
          <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {{feature}}
        </li>
      ))}}
    </ul>
    <CheckoutButton priceId={{priceId}} label="Get Started" className="w-full mt-6" />
  </div>
);
'''
        return code
    
    def _generate_storage_code(self, config: Dict) -> str:
        """Generate file storage code."""
        return '''
// ═══════════════════════════════════════════════════════════════════════════════
// FILE STORAGE
// ═══════════════════════════════════════════════════════════════════════════════

// Upload file to Supabase Storage
const uploadFile = async (file, bucket = "files", path = null) => {
  const supabase = await getSupabase();
  
  const filePath = path || `${Date.now()}_${file.name}`;
  
  const { data, error } = await supabase.storage
    .from(bucket)
    .upload(filePath, file);
  
  if (error) throw error;
  
  // Get public URL
  const { data: { publicUrl } } = supabase.storage
    .from(bucket)
    .getPublicUrl(filePath);
  
  return { path: data.path, url: publicUrl };
};

// Delete file
const deleteFile = async (path, bucket = "files") => {
  const supabase = await getSupabase();
  const { error } = await supabase.storage.from(bucket).remove([path]);
  if (error) throw error;
};

// File Upload Component
const FileUpload = ({ onUpload, accept = "image/*", bucket = "files" }) => {
  const [uploading, setUploading] = React.useState(false);
  const [preview, setPreview] = React.useState(null);
  
  const handleChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Show preview
    if (file.type.startsWith("image/")) {
      setPreview(URL.createObjectURL(file));
    }
    
    setUploading(true);
    try {
      const result = await uploadFile(file, bucket);
      if (onUpload) onUpload(result);
    } catch (err) {
      console.error("Upload error:", err);
      alert("Upload failed: " + err.message);
    }
    setUploading(false);
  };
  
  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
      <input
        type="file"
        accept={accept}
        onChange={handleChange}
        className="hidden"
        id="file-upload"
        disabled={uploading}
      />
      <label htmlFor="file-upload" className="cursor-pointer">
        {preview ? (
          <img src={preview} alt="Preview" className="max-h-40 mx-auto rounded" />
        ) : (
          <div className="text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p>{uploading ? "Uploading..." : "Click to upload"}</p>
          </div>
        )}
      </label>
    </div>
  );
};
'''


# Singleton
service_code_generator = ServiceCodeGenerator()


