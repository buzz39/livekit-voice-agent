import { NextRequest, NextResponse } from 'next/server';
import pool from '@/utils/db';

export async function POST(request: NextRequest) {
    let client;
    try {
        client = await pool.connect();
        const data = await request.json();
        const { slug, opening_line, mcp_endpoint_url, is_active, owner_id } = data;

        if (!slug) {
            return NextResponse.json({ error: 'Slug is required' }, { status: 400 });
        }

        // Check if agent exists
        const existing = await client.query(
            `SELECT * FROM agent_configs WHERE slug = $1`,
            [slug]
        );

        if (existing.rows.length > 0) {
            // Update
            await client.query(
                `UPDATE agent_configs SET opening_line = $1, mcp_endpoint_url = $2, is_active = $3, updated_at = NOW()
                 WHERE slug = $4`,
                [opening_line || '', mcp_endpoint_url || '', is_active ?? true, slug]
            );
            console.log('Agent updated:', slug);
        } else {
            // Create
            await client.query(
                `INSERT INTO agent_configs (slug, owner_id, opening_line, mcp_endpoint_url, is_active)
                 VALUES ($1, $2, $3, $4, $5)`,
                [slug, owner_id || 'dev_user', opening_line || '', mcp_endpoint_url || '', is_active ?? true]
            );
            console.log('Agent created:', slug);
        }

        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error('Database error:', error);
        return NextResponse.json({ error: error.message || 'Failed to save agent' }, { status: 500 });
    } finally {
        if (client) {
            client.release();
        }
    }
}

export async function DELETE(request: NextRequest) {
    let client;
    try {
        client = await pool.connect();
        const body = await request.json();
        const { slug } = body;
        if (!slug) {
            return NextResponse.json({ error: 'Slug is required' }, { status: 400 });
        }
        await client.query(`DELETE FROM agent_configs WHERE slug = $1`, [slug]);
        console.log('Agent deleted:', slug);
        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error('Database error:', error);
        return NextResponse.json({ error: error.message || 'Failed to delete agent' }, { status: 500 });
    } finally {
        if (client) {
            client.release();
        }
    }
}
