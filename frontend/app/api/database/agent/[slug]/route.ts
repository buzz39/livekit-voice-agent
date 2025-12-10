import { NextRequest, NextResponse } from 'next/server';
import pool from '@/utils/db';

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ slug: string }> }) {
    const client = await pool.connect();
    try {
        const { slug } = await params;
        await client.query(`DELETE FROM agent_configs WHERE slug = $1`, [slug]);
        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Database error:', error);
        return NextResponse.json({ error: 'Failed to delete agent' }, { status: 500 });
    } finally {
        client.release();
    }
}
