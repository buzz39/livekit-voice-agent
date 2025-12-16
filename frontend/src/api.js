// Frontend API Client

const API_BASE_URL = 'http://localhost:8000';

export async function getStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    return null;
  }
}

export async function getRecentCalls(limit = 10) {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/calls?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch calls:", error);
    return [];
  }
}

export async function getCallDetails(callId) {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/call/${callId}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Failed to fetch call details for ${callId}:`, error);
    return null;
  }
}

export async function startOutboundCall(phoneNumber, businessName = "Default Business") {
  try {
    const response = await fetch(`${API_BASE_URL}/outbound-call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        phone_number: phoneNumber,
        business_name: businessName,
        agent_slug: 'default_roofing_agent' // Configurable if needed
      }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to start call:", error);
    throw error;
  }
}
