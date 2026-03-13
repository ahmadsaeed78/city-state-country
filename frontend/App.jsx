import { useState, useEffect } from "react";
import { Country, State, City } from "country-state-city";
import axios from "axios";

const API = "http://localhost:8000/api";

// ── Minimal inline styles (no MUI needed) ─────────────────────────────────────
const s = {
  page:    { minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f0f2f5", fontFamily: "system-ui, sans-serif" },
  card:    { background: "#fff", borderRadius: 12, padding: "40px 36px", width: "100%", maxWidth: 500, boxShadow: "0 4px 24px rgba(0,0,0,0.10)" },
  title:   { fontSize: 24, fontWeight: 700, marginBottom: 24, color: "#1a1a2e" },
  field:   { marginBottom: 16 },
  label:   { display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4, color: "#374151" },
  input:   { width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 15, boxSizing: "border-box", outline: "none", background: "#fff" },
  select:  { width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 15, boxSizing: "border-box", background: "#fff", cursor: "pointer" },
  disabled:{ background: "#f3f4f6", cursor: "not-allowed", color: "#9ca3af" },
  error:   { fontSize: 12, color: "#dc2626", marginTop: 4 },
  btn:     { width: "100%", padding: "12px", background: "#4f46e5", color: "#fff", border: "none", borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: "pointer", marginTop: 8 },
  success: { background: "#d1fae5", color: "#065f46", padding: "12px 16px", borderRadius: 8, marginBottom: 16, fontSize: 14 },
  errBox:  { background: "#fee2e2", color: "#991b1b", padding: "12px 16px", borderRadius: 8, marginBottom: 16, fontSize: 14 },
};

export default function App() {
  // Form state
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "",
    phone: "", postal_code: "",
  });

  // Location state
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [selectedState,   setSelectedState]   = useState(null);
  const [selectedCity,    setSelectedCity]     = useState(null);

  // Derived lists
  const allCountries  = Country.getAllCountries();
  const [states,  setStates]  = useState([]);
  const [cities,  setCities]  = useState([]);

  // UI state
  const [errors,  setErrors]  = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [apiErr,  setApiErr]  = useState("");

  // ── Cascading: when country changes ──────────────────────────────────────────
  useEffect(() => {
    if (!selectedCountry) {
      setStates([]);
      setCities([]);
      setSelectedState(null);
      setSelectedCity(null);
      return;
    }
    const s = State.getStatesOfCountry(selectedCountry.isoCode);
    setStates(s);
    setCities([]);
    setSelectedState(null);
    setSelectedCity(null);
  }, [selectedCountry]);

  // ── Cascading: when state changes ────────────────────────────────────────────
  useEffect(() => {
    if (!selectedState || !selectedCountry) {
      setCities([]);
      setSelectedCity(null);
      return;
    }
    const c = City.getCitiesOfState(selectedCountry.isoCode, selectedState.isoCode);
    setCities(c);
    setSelectedCity(null);
  }, [selectedState]);

  // ── Helpers ───────────────────────────────────────────────────────────────────
  const handleInput = (e) => {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
    setErrors(er => ({ ...er, [e.target.name]: "" }));
  };

  const validate = () => {
    const e = {};
    if (!form.first_name.trim()) e.first_name = "Required";
    if (!form.last_name.trim())  e.last_name  = "Required";
    if (!form.email.trim())      e.email      = "Required";
    if (!form.phone.trim())      e.phone      = "Required";
    if (!form.postal_code.trim()) e.postal_code = "Required";
    if (!selectedCountry)        e.country    = "Required";
    if (states.length > 0 && !selectedState) e.state = "Required";
    if (cities.length > 0 && !selectedCity)  e.city  = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // ── Submit ────────────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccess("");
    setApiErr("");

    if (!validate()) return;

    const payload = {
      ...form,
      // Send full names — backend uses country-state-city with same names
      country: selectedCountry?.name     ?? "",
      state:   selectedState?.name       ?? "",  // "" when country has no states
      city:    selectedCity?.name        ?? "",  // "" when state has no cities
    };

    setLoading(true);
    try {
      const res = await axios.post(`${API}/users`, payload);
      setSuccess(`User created! ID: ${res.data.id}`);
      // Reset
      setForm({ first_name: "", last_name: "", email: "", phone: "", postal_code: "" });
      setSelectedCountry(null);
      setSelectedState(null);
      setSelectedCity(null);
    } catch (err) {
      if (err.response?.status === 422) {
        // Pydantic validation errors
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          const mapped = {};
          detail.forEach(d => {
            const field = d.loc?.[d.loc.length - 1] ?? "general";
            mapped[field] = d.msg.replace("Value error, ", "");
          });
          setErrors(mapped);
        } else {
          setApiErr(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
      } else if (err.response?.status === 400) {
        setApiErr(err.response.data.detail ?? "Request failed");
      } else {
        setApiErr("Network error — is the backend running?");
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────────
  const inp = (name, label, type = "text", placeholder = "") => (
    <div style={s.field}>
      <label style={s.label}>{label}</label>
      <input
        style={{ ...s.input, ...(errors[name] ? { borderColor: "#dc2626" } : {}) }}
        name={name} type={type} value={form[name]}
        onChange={handleInput} placeholder={placeholder}
      />
      {errors[name] && <div style={s.error}>{errors[name]}</div>}
    </div>
  );

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.title}>Create User</div>

        {success && <div style={s.success}>{success}</div>}
        {apiErr  && <div style={s.errBox}>{apiErr}</div>}

        <form onSubmit={handleSubmit} noValidate>
          {inp("first_name", "First Name")}
          {inp("last_name",  "Last Name")}
          {inp("email",      "Email", "email")}

          {/* Country */}
          <div style={s.field}>
            <label style={s.label}>Country *</label>
            <select
              style={{ ...s.select, ...(errors.country ? { borderColor: "#dc2626" } : {}) }}
              value={selectedCountry?.isoCode ?? ""}
              onChange={e => {
                const c = allCountries.find(x => x.isoCode === e.target.value) ?? null;
                setSelectedCountry(c);
                setErrors(er => ({ ...er, country: "" }));
              }}
            >
              <option value="">— Select country —</option>
              {allCountries.map(c => (
                <option key={c.isoCode} value={c.isoCode}>{c.name}</option>
              ))}
            </select>
            {errors.country && <div style={s.error}>{errors.country}</div>}
          </div>

          {/* State — disabled when country has no states */}
          <div style={s.field}>
            <label style={s.label}>
              State / Province {states.length > 0 ? "*" : "(not applicable)"}
            </label>
            <select
              style={{
                ...s.select,
                ...(states.length === 0 || !selectedCountry ? s.disabled : {}),
                ...(errors.state ? { borderColor: "#dc2626" } : {}),
              }}
              disabled={states.length === 0 || !selectedCountry}
              value={selectedState?.isoCode ?? ""}
              onChange={e => {
                const st = states.find(x => x.isoCode === e.target.value) ?? null;
                setSelectedState(st);
                setErrors(er => ({ ...er, state: "" }));
              }}
            >
              <option value="">
                {states.length === 0 ? "No states for this country" : "— Select state —"}
              </option>
              {states.map(st => (
                <option key={st.isoCode} value={st.isoCode}>{st.name}</option>
              ))}
            </select>
            {errors.state && <div style={s.error}>{errors.state}</div>}
          </div>

          {/* City — disabled when state has no cities */}
          <div style={s.field}>
            <label style={s.label}>
              City {cities.length > 0 ? "*" : "(not applicable)"}
            </label>
            <select
              style={{
                ...s.select,
                ...(cities.length === 0 || !selectedState ? s.disabled : {}),
                ...(errors.city ? { borderColor: "#dc2626" } : {}),
              }}
              disabled={cities.length === 0 || !selectedState}
              value={selectedCity?.name ?? ""}
              onChange={e => {
                const ci = cities.find(x => x.name === e.target.value) ?? null;
                setSelectedCity(ci);
                setErrors(er => ({ ...er, city: "" }));
              }}
            >
              <option value="">
                {cities.length === 0 ? "No cities for this state" : "— Select city —"}
              </option>
              {cities.map(ci => (
                <option key={ci.name + ci.stateCode} value={ci.name}>{ci.name}</option>
              ))}
            </select>
            {errors.city && <div style={s.error}>{errors.city}</div>}
          </div>

          {inp("phone",       "Phone (E.164 e.g. +923001234567)", "tel")}
          {inp("postal_code", "Postal Code")}

          {/* Show geo error if returned from backend */}
          {(errors.country || errors.state || errors.city) && (
            <div style={s.errBox}>
              {errors.country || errors.state || errors.city}
            </div>
          )}

          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? "Creating..." : "Create User"}
          </button>
        </form>
      </div>
    </div>
  );
}
