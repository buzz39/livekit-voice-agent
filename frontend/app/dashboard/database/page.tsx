'use client';

export const dynamic = 'force-dynamic';

import { useState } from 'react';
import { Database, Trash2, Save } from 'lucide-react';

interface TableData {
    [key: string]: any;
}

interface TableInfo {
    name: string;
    columns: string[];
    rows: TableData[];
}

export default function DatabasePortal() {
    const [databaseUrl, setDatabaseUrl] = useState('');
    const [inputUrl, setInputUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [tables, setTables] = useState<TableInfo[]>([]);
    const [selectedTable, setSelectedTable] = useState<string | null>(null);
    const [selectedRow, setSelectedRow] = useState<number | null>(null);
    const [editingRow, setEditingRow] = useState<TableData>({});

    const connectDatabase = async () => {
        if (!inputUrl.trim()) {
            setMessage('Please enter a database URL');
            return;
        }

        setLoading(true);
        setMessage('Connecting...');

        try {
            const response = await fetch('/api/database/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: inputUrl }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to connect');
            }

            setDatabaseUrl(inputUrl);
            setTables(data.tables || []);
            setMessage('Connected successfully');
            setInputUrl('');
        } catch (error: any) {
            setMessage(`Connection error: ${error.message}`);
        }
        setLoading(false);
    };

    const handleSelectTable = (tableName: string) => {
        setSelectedTable(tableName);
        setSelectedRow(null);
        setEditingRow({});
    };

    const handleSelectRow = (index: number, row: TableData) => {
        setSelectedRow(index);
        setEditingRow({ ...row });
    };

    const handleSaveRow = async () => {
        if (selectedRow === null || !selectedTable) return;

        setLoading(true);
        try {
            const response = await fetch('/api/database/update-row', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: databaseUrl,
                    table: selectedTable,
                    row: editingRow,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to save');
            }

            setMessage('Row saved successfully');
            // Refresh table data
            const table = tables.find((t) => t.name === selectedTable);
            if (table) {
                table.rows[selectedRow] = editingRow;
            }
        } catch (error: any) {
            setMessage(`Save error: ${error.message}`);
        }
        setLoading(false);
    };

    const handleDeleteRow = async () => {
        if (selectedRow === null || !selectedTable || !confirm('Delete this row?')) return;

        setLoading(true);
        try {
            const response = await fetch('/api/database/delete-row', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: databaseUrl,
                    table: selectedTable,
                    row: editingRow,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to delete');
            }

            setMessage('Row deleted successfully');
            // Remove from local state
            const table = tables.find((t) => t.name === selectedTable);
            if (table && selectedRow !== null) {
                table.rows.splice(selectedRow, 1);
            }
            setSelectedRow(null);
            setEditingRow({});
        } catch (error: any) {
            setMessage(`Delete error: ${error.message}`);
        }
        setLoading(false);
    };

    const currentTable = tables.find((t) => t.name === selectedTable);

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <Database className="h-8 w-8 text-blue-500" />
                <h1 className="text-3xl font-bold dark:text-white">Database Editor</h1>
            </div>

            {/* Connection Section */}
            {!databaseUrl ? (
                <div className="bg-white dark:bg-zinc-900 border dark:border-zinc-800 rounded-lg p-6 max-w-md">
                    <h2 className="text-xl font-semibold mb-4 dark:text-white">Connect to Neon Database</h2>
                    <div className="space-y-3">
                        <div>
                            <label className="block text-sm font-medium mb-2 dark:text-zinc-300">Database URL</label>
                            <textarea
                                value={inputUrl}
                                onChange={(e) => setInputUrl(e.target.value)}
                                placeholder="postgresql://user:password@host/dbname"
                                className="w-full px-3 py-2 border dark:border-zinc-700 rounded text-sm h-24 dark:bg-zinc-800 dark:text-white"
                            />
                        </div>
                        <button
                            onClick={connectDatabase}
                            disabled={loading || !inputUrl.trim()}
                            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? 'Connecting...' : 'Connect'}
                        </button>
                    </div>
                    {message && (
                        <div className={`mt-3 p-2 rounded text-sm ${message.includes('error') ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-100' : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-100'}`}>
                            {message}
                        </div>
                    )}
                </div>
            ) : (
                <>
                    {/* Connected State */}
                    <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600 dark:text-green-300">Connected to Neon Database</p>
                            <p className="text-xs text-gray-500 dark:text-green-400 mt-1 break-all">{databaseUrl.substring(0, 50)}...</p>
                        </div>
                        <button
                            onClick={() => {
                                setDatabaseUrl('');
                                setInputUrl('');
                                setTables([]);
                                setSelectedTable(null);
                                setMessage('');
                            }}
                            className="px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                        >
                            Disconnect
                        </button>
                    </div>

                    {/* Message */}
                    {message && (
                        <div className={`p-3 rounded ${message.includes('error') ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-100' : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-100'}`}>
                            {message}
                        </div>
                    )}

                    {/* Tables and Data */}
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                        {/* Tables List */}
                        <div className="lg:col-span-1">
                            <h2 className="font-semibold text-lg mb-3 dark:text-white">Tables</h2>
                            <div className="space-y-2 border dark:border-zinc-800 rounded-lg p-2 bg-white dark:bg-zinc-900">
                                {tables.length === 0 ? (
                                    <p className="text-sm text-gray-500 p-2">No tables found</p>
                                ) : (
                                    tables.map((table) => (
                                        <button
                                            key={table.name}
                                            onClick={() => handleSelectTable(table.name)}
                                            className={`w-full text-left p-3 rounded border transition-colors text-sm ${
                                                selectedTable === table.name
                                                    ? 'bg-blue-100 dark:bg-blue-900 border-blue-500'
                                                    : 'border-gray-200 dark:border-zinc-700 hover:border-blue-400 dark:hover:border-blue-600'
                                            }`}
                                        >
                                            <div className="font-medium dark:text-white">{table.name}</div>
                                            <div className="text-xs text-gray-600 dark:text-gray-400">{table.rows.length} rows</div>
                                        </button>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Rows List and Editor */}
                        <div className="lg:col-span-3">
                            {currentTable ? (
                                <div className="space-y-4">
                                    {/* Rows List */}
                                    <div>
                                        <h2 className="font-semibold text-lg mb-3 dark:text-white">Rows</h2>
                                        <div className="border dark:border-zinc-800 rounded-lg max-h-96 overflow-y-auto bg-white dark:bg-zinc-900">
                                            {currentTable.rows.length === 0 ? (
                                                <p className="text-sm text-gray-500 p-4">No rows in this table</p>
                                            ) : (
                                                <div className="space-y-1 p-2">
                                                    {currentTable.rows.map((row, idx) => (
                                                        <button
                                                            key={idx}
                                                            onClick={() => handleSelectRow(idx, row)}
                                                            className={`w-full text-left p-3 rounded border transition-colors text-sm ${
                                                                selectedRow === idx
                                                                    ? 'bg-blue-100 dark:bg-blue-900 border-blue-500'
                                                                    : 'border-gray-200 dark:border-zinc-700 hover:border-blue-400 dark:hover:border-blue-600'
                                                            }`}
                                                        >
                                                            <div className="font-medium dark:text-white">Row {idx + 1}</div>
                                                            <div className="text-xs text-gray-600 dark:text-gray-400">
                                                                {Object.entries(row)
                                                                    .slice(0, 2)
                                                                    .map(([k, v]) => `${k}: ${String(v).substring(0, 20)}`)
                                                                    .join(' | ')}
                                                            </div>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Row Editor */}
                                    {selectedRow !== null && (
                                        <div className="bg-white dark:bg-zinc-900 border dark:border-zinc-800 rounded-lg p-6">
                                            <h3 className="text-lg font-semibold mb-4 dark:text-white">Edit Row {selectedRow + 1}</h3>
                                            <div className="space-y-3 max-h-96 overflow-y-auto mb-4">
                                                {currentTable.columns.map((col) => (
                                                    <div key={col}>
                                                        <label className="block text-sm font-medium mb-1 dark:text-zinc-300">{col}</label>
                                                        <input
                                                            type="text"
                                                            value={editingRow[col] ?? ''}
                                                            onChange={(e) =>
                                                                setEditingRow({
                                                                    ...editingRow,
                                                                    [col]: e.target.value,
                                                                })
                                                            }
                                                            className="w-full px-3 py-2 border dark:border-zinc-700 rounded text-sm dark:bg-zinc-800 dark:text-white"
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={handleSaveRow}
                                                    disabled={loading}
                                                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                                >
                                                    <Save className="h-4 w-4" /> Save
                                                </button>
                                                <button
                                                    onClick={handleDeleteRow}
                                                    disabled={loading}
                                                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                                                >
                                                    <Trash2 className="h-4 w-4" /> Delete
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                                    <p>Select a table to view and edit rows</p>
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
