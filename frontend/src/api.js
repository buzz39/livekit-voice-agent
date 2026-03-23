// Frontend API Client

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://livekit-outbound-api.tinysaas.fun';
const API_SECRET_KEY = import.meta.env.VITE_API_SECRET_KEY || '';
export const apiEvents = new EventTarget();

function emitApiError(message) {
  apiEvents.dispatchEvent(new CustomEvent('error', { detail: { message } }));
}

// Helper to get Stack Auth session token
async function getAuthHeaders() {
  const headers = {};
  // Add API key if configured
  if (API_SECRET_KEY) {
    headers['x-api-key'] = API_SECRET_KEY;
  }
  try {
    // Stack Auth stores the app instance on window after initialization
    if (window.__stackClientApp) {
      const user = await window.__stackClientApp.getUser();
      if (user) {
        const token = await user.getAuthJson();
        if (token?.accessToken) {
          headers['Authorization'] = `Bearer ${token.accessToken}`;
        }
      }
    }
  } catch {
    // Silently fail — auth headers are optional until backend enforces them
  }
  return headers;
}

async function apiFetch(path, options = {}) {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...(options.headers || {}),
    },
  });
  return response;
}

export async function getStats() {
  try {
    const response = await apiFetch('/dashboard/stats');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    emitApiError('Unable to load dashboard stats right now.');
    return null;
  }
}

export async function getAnalyticsVolume(days = 30) {
  try {
    const response = await apiFetch(`/dashboard/analytics/volume?days=${days}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch analytics:", error);
    emitApiError('Unable to load analytics right now.');
    return [];
  }
}

export async function getRecentCalls(limit = 10) {
  try {
    const response = await apiFetch(`/dashboard/calls?limit=${limit}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    return data.map(call => {
      if (call.recording_url && !call.recording_url.startsWith('http')) {
        call.recording_url = `${API_BASE_URL}${call.recording_url.startsWith('/') ? '' : '/'}${call.recording_url}`;
      }
      return call;
    });
  } catch (error) {
    console.error("Failed to fetch calls:", error);
    emitApiError('Unable to load recent calls right now.');
    return [];
  }
}

export async function getAppointments() {
  try {
    const response = await apiFetch('/dashboard/appointments');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch appointments:", error);
    emitApiError('Unable to load appointments right now.');
    return [];
  }
}

export const getAllPrompts = async (industry = null) => {
  try {
    const url = industry ? `/dashboard/prompts?industry=${encodeURIComponent(industry)}` : '/dashboard/prompts';
    const response = await apiFetch(url);
    if (!response.ok) throw new Error('Failed to fetch prompts');
    return await response.json();
  } catch (error) {
    console.error('Error fetching prompts:', error);
    emitApiError('Unable to load prompts right now.');
    return [];
  }
};

export const getActivePrompt = async (name = "default_roofing_agent") => {
  try {
    const response = await apiFetch(`/dashboard/prompt?name=${name}`);
    if (!response.ok) throw new Error('Failed to fetch prompt');
    return await response.json();
  } catch (error) {
    console.error('Error fetching prompt:', error);
    emitApiError('Unable to load the current prompt right now.');
    return null;
  }
};

export const updateActivePrompt = async (content, name = "default_roofing_agent") => {
  try {
    const response = await apiFetch('/dashboard/prompt', {
      method: 'POST',
      body: JSON.stringify({ name, content }),
    });
    if (!response.ok) throw new Error('Failed to update prompt');
    return await response.json();
  } catch (error) {
    console.error('Error updating prompt:', error);
    throw error;
  }
};

export async function getCallDetails(callId) {
  try {
    const response = await apiFetch(`/dashboard/call/${callId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (data && data.recording_url && !data.recording_url.startsWith('http')) {
      data.recording_url = `${API_BASE_URL}${data.recording_url.startsWith('/') ? '' : '/'}${data.recording_url}`;
    }
    return data;
  } catch (error) {
    console.error(`Failed to fetch call details for ${callId}:`, error);
    emitApiError('Unable to load call details right now.');
    return null;
  }
}

export async function saveAgentConfig(config) {
  const response = await apiFetch('/api/config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function startOutboundCall(phoneNumber, businessName = "Default Business", agentSlug = "default_roofing_agent", fromNumber = null) {
  try {
    const body = {
      phone_number: phoneNumber,
      business_name: businessName,
      agent_slug: agentSlug,
    };
    if (fromNumber) {
      body.from_number = fromNumber;
    }
    const response = await apiFetch('/outbound-call', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to start call:", error);
    throw error;
  }
}

// --- Prompt CRUD ---

export async function getPromptById(promptId) {
  const response = await apiFetch(`/dashboard/prompt/${promptId}`);
  if (!response.ok) throw new Error('Failed to fetch prompt');
  return await response.json();
}

export async function createPrompt({ name, content, industry = 'general', description = '', is_active = true }) {
  const response = await apiFetch('/dashboard/prompts', {
    method: 'POST',
    body: JSON.stringify({ name, content, industry, description, is_active }),
  });
  if (!response.ok) throw new Error('Failed to create prompt');
  return await response.json();
}

export async function patchPrompt(promptId, fields) {
  const response = await apiFetch(`/dashboard/prompt/${promptId}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  });
  if (!response.ok) throw new Error('Failed to update prompt');
  return await response.json();
}

export async function deletePrompt(promptId) {
  const response = await apiFetch(`/dashboard/prompt/${promptId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete prompt');
  return await response.json();
}

export async function clonePrompt(promptId, newName, newIndustry) {
  const response = await apiFetch(`/dashboard/prompt/${promptId}/clone`, {
    method: 'POST',
    body: JSON.stringify({ new_name: newName, new_industry: newIndustry }),
  });
  if (!response.ok) throw new Error('Failed to clone prompt');
  return await response.json();
}

export async function getIndustries() {
  try {
    const response = await apiFetch('/dashboard/industries');
    if (!response.ok) throw new Error('Failed to fetch industries');
    return await response.json();
  } catch (error) {
    console.error('Error fetching industries:', error);
    return [];
  }
}

// --- Agent Config CRUD ---

export async function getAgents() {
  try {
    const response = await apiFetch('/dashboard/agents');
    if (!response.ok) throw new Error('Failed to fetch agents');
    return await response.json();
  } catch (error) {
    console.error('Error fetching agents:', error);
    return [];
  }
}

export async function upsertAgent(agent) {
  const response = await apiFetch('/dashboard/agents', {
    method: 'POST',
    body: JSON.stringify(agent),
  });
  if (!response.ok) throw new Error('Failed to save agent');
  return await response.json();
}

export async function deleteAgent(slug) {
  const response = await apiFetch(`/dashboard/agent/${encodeURIComponent(slug)}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete agent');
  return await response.json();
}

// --- Data Schema CRUD ---

export async function getDataSchemas(slug = null) {
  try {
    const url = slug ? `/dashboard/data-schemas?slug=${encodeURIComponent(slug)}` : '/dashboard/data-schemas';
    const response = await apiFetch(url);
    if (!response.ok) throw new Error('Failed to fetch schemas');
    return await response.json();
  } catch (error) {
    console.error('Error fetching data schemas:', error);
    return [];
  }
}

export async function createDataSchemaField(field) {
  const response = await apiFetch('/dashboard/data-schemas', {
    method: 'POST',
    body: JSON.stringify(field),
  });
  if (!response.ok) throw new Error('Failed to create schema field');
  return await response.json();
}

export async function deleteDataSchemaField(fieldId) {
  const response = await apiFetch(`/dashboard/data-schema/${fieldId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete schema field');
  return await response.json();
}

// --- Test Call with specific prompt ---

export async function startTestCall({ phone_number, prompt_id, business_name = '', agent_slug = 'default_roofing_agent', from_number = null }) {
  const body = { phone_number, prompt_id, business_name, agent_slug };
  if (from_number) body.from_number = from_number;
  const response = await apiFetch('/dashboard/test-call', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// --- AI Config CRUD ---

export async function getAllAiConfigs() {
  try {
    const response = await apiFetch('/dashboard/ai-configs');
    if (!response.ok) throw new Error('Failed to fetch AI configs');
    return await response.json();
  } catch (error) {
    console.error('Error fetching AI configs:', error);
    return [];
  }
}

export async function getAiConfig(name) {
  try {
    const response = await apiFetch(`/dashboard/ai-config?name=${encodeURIComponent(name)}`);
    if (!response.ok) throw new Error('Failed to fetch AI config');
    return await response.json();
  } catch (error) {
    console.error('Error fetching AI config:', error);
    return null;
  }
}

export async function upsertAiConfig(config) {
  const response = await apiFetch('/dashboard/ai-configs', {
    method: 'POST',
    body: JSON.stringify(config),
  });
  if (!response.ok) throw new Error('Failed to save AI config');
  return await response.json();
}

// --- Objection CRUD ---

export async function getObjections(agentSlug = null) {
  try {
    const url = agentSlug ? `/dashboard/objections?agent_slug=${encodeURIComponent(agentSlug)}` : '/dashboard/objections';
    const response = await apiFetch(url);
    if (!response.ok) throw new Error('Failed to fetch objections');
    return await response.json();
  } catch (error) {
    console.error('Error fetching objections:', error);
    return [];
  }
}

export async function upsertObjection(objection) {
  const response = await apiFetch('/dashboard/objections', {
    method: 'POST',
    body: JSON.stringify(objection),
  });
  if (!response.ok) throw new Error('Failed to save objection');
  return await response.json();
}

export async function deleteObjection(id) {
  const response = await apiFetch(`/dashboard/objection/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete objection');
  return await response.json();
}
