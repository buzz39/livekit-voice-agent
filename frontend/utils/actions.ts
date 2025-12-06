'use server';

import pool from './db';
import { stackServerApp } from '../stack';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';

export async function getAgents() {
    // const user = await stackServerApp.getUser();
    // if (!user) return [];
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const client = await pool.connect();
    try {
        const res = await client.query(
            `SELECT * FROM agent_configs WHERE owner_id = $1 ORDER BY created_at DESC`,
            [user.id]
        );
        return res.rows;
    } finally {
        client.release();
    }
}

export async function createAgent(formData: FormData) {
    // const user = await stackServerApp.getUser();
    // if (!user) throw new Error('Unauthorized');
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const name = formData.get('name') as string;
    const slug = formData.get('slug') as string;

    if (!slug || !name) {
        throw new Error("Name and Slug are required");
    }

    const client = await pool.connect();
    try {
        await client.query(
            `INSERT INTO agent_configs (slug, owner_id, opening_line, is_active) 
             VALUES ($1, $2, $3, true)
             ON CONFLICT (slug) DO NOTHING`,
            [slug, user.id, `Hello! I am ${name}. How can I help you?`]
        );

    } catch (e) {
        console.error(e);
        throw new Error("Failed to create agent. Slug might be taken.");
    } finally {
        client.release();
    }

    revalidatePath('/dashboard/agents');
    redirect(`/dashboard/agents/${slug}`);
}

export async function getAgentDetails(slug: string) {
    // const user = await stackServerApp.getUser();
    // if (!user) return null;
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const client = await pool.connect();
    try {
        const agentRes = await client.query(
            `SELECT * FROM agent_configs WHERE slug = $1 AND owner_id = $2`,
            [slug, user.id]
        );
        const agent = agentRes.rows[0];
        if (!agent) return null;

        // Fetch related data in parallel
        const [promptsRes, aiConfigRes, schemaRes, webhooksRes] = await Promise.all([
            client.query(`SELECT content, is_active FROM prompts WHERE name = $1 AND owner_id = $2`, [slug, user.id]),
            client.query(`SELECT * FROM ai_configs WHERE name = $1 AND(owner_id = $2 OR owner_id IS NULL)`, [slug, user.id]),
            client.query(`SELECT * FROM data_schemas WHERE slug = $1 AND owner_id = $2`, [slug, user.id]),
            client.query(`SELECT * FROM webhook_configs WHERE slug = $1 AND owner_id = $2`, [slug, user.id])
        ]);

        return {
            ...agent,
            prompt: promptsRes.rows.find((r: any) => r.is_active)?.content || '',
            ai_config: aiConfigRes.rows[0] || {},
            data_schema: schemaRes.rows,
            webhooks: webhooksRes.rows
        };
    } finally {
        client.release();
    }
}

export async function updateAgent(slug: string, data: any) {
    // const user = await stackServerApp.getUser();
    // if (!user) throw new Error("Unauthorized");
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const client = await pool.connect();
    try {
        await client.query('BEGIN');

        // Update Agent Config
        await client.query(
            `UPDATE agent_configs SET opening_line = $1, mcp_endpoint_url = $2 WHERE slug = $3 AND owner_id = $4`,
            [data.opening_line, data.mcp_endpoint_url, slug, user.id]
        );

        // Update Prompt (Upsert)
        await client.query(
            `INSERT INTO prompts(name, owner_id, content, is_active) 
             VALUES($1, $2, $3, true)
             ON CONFLICT(name) DO UPDATE SET content = $3, updated_at = NOW()`,
            [slug, user.id, data.prompt]
        );

        // Update AI Config (Upsert)
        await client.query(
            `INSERT INTO ai_configs(name, owner_id, llm_model, stt_model, tts_voice, tts_speed)
             VALUES($1, $2, $3, $4, $5, $6)
             ON CONFLICT(name) DO UPDATE SET 
                llm_model = $3, stt_model = $4, tts_voice = $5, tts_speed = $6`,
            [slug, user.id, data.ai_config.llm_model, data.ai_config.stt_model, data.ai_config.tts_voice, data.ai_config.tts_speed]
        );

        // Data Schema - simplified: delete all and recreate
        await client.query(`DELETE FROM data_schemas WHERE slug = $1 AND owner_id = $2`, [slug, user.id]);

        if (data.data_schema && Array.isArray(data.data_schema)) {
            for (const field of data.data_schema) {
                await client.query(
                    `INSERT INTO data_schemas(slug, owner_id, field_name, description, field_type)
                     VALUES($1, $2, $3, $4, $5)`,
                    [slug, user.id, field.field_name, field.description, field.field_type]
                );
            }
        }

        await client.query('COMMIT');
    } catch (e) {
        await client.query('ROLLBACK');
        console.error("Update failed", e);
        throw new Error("Failed to update agent");
    } finally {
        client.release();
    }

    revalidatePath(`/dashboard/agents/${slug}`);
}

export async function getCallLogs() {
    // const user = await stackServerApp.getUser();
    // if (!user) return [];
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const client = await pool.connect();
    try {
        const res = await client.query(`
            SELECT 
                c.id, c.created_at, c.duration_seconds, c.call_status, c.end_reason,
                c.interest_level, c.transcript,
                co.phone_number, co.business_name
            FROM calls c
            LEFT JOIN contacts co ON c.contact_id = co.id
            WHERE c.owner_id = $1
            ORDER BY c.created_at DESC
            LIMIT 50
        `, [user.id]);
        return res.rows;
    } finally {
        client.release();
    }
}

export async function addWebhook(slug: string, targetUrl: string, eventType: string) {
    // const user = await stackServerApp.getUser();
    // if (!user) throw new Error("Unauthorized");
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const client = await pool.connect();
    try {
        const res = await client.query(
            `INSERT INTO webhook_configs(slug, owner_id, target_url, event_type, is_active)
             VALUES($1, $2, $3, $4, true)
             RETURNING * `,
            [slug, user.id, targetUrl, eventType]
        );
        return res.rows[0];
    } finally {
        client.release();
    }
}

export async function deleteWebhook(id: number) {
    // const user = await stackServerApp.getUser();
    // if (!user) throw new Error("Unauthorized");
    const user = { id: 'dev_user', displayName: 'Dev User' };

    const client = await pool.connect();
    try {
        await client.query(
            `DELETE FROM webhook_configs WHERE id = $1 AND owner_id = $2`,
            [id, user.id]
        );
    } finally {
        client.release();
    }
}

export async function triggerOutboundCall(phoneNumber: string, agentSlug: string) {
    // NOTE: In production, validate user owns this agent

    try {
        const response = await fetch('http://localhost:8000/outbound-call', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                phone_number: phoneNumber,
                business_name: "Test Call", // Or fetch from user context
                agent_slug: agentSlug
            }),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to trigger call: ${error}`);
        }

        return await response.json();
    } catch (e) {
        console.error("Trigger Call Error:", e);
        throw e;
    }
}
