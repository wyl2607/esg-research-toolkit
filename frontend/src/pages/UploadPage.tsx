import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation } from '@tanstack/react-query'
import { uploadReport } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'
import { useNavigate } from 'react-router-dom'

export function UploadPage() {
  const navigate = useNavigate()
  const [result, setResult] = useState<CompanyESGData | null>(null)

  const mutation = useMutation({
    mutationFn: uploadReport,
    onSuccess: (data) => setResult(data),
  })

  const onDrop = useCallback(
    (files: File[]) => {
      if (files[0]) mutation.mutate(files[0])
    },
    [mutation]
  )

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    acceptedFiles,
  } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
  })

  const fields: [string, string][] = result
    ? [
        [
          'Scope 1 CO₂e',
          result.scope1_co2e_tonnes != null
            ? `${result.scope1_co2e_tonnes.toLocaleString()} t`
            : '—',
        ],
        [
          'Scope 2 CO₂e',
          result.scope2_co2e_tonnes != null
            ? `${result.scope2_co2e_tonnes.toLocaleString()} t`
            : '—',
        ],
        [
          'Renewable Energy',
          result.renewable_energy_pct != null
            ? `${result.renewable_energy_pct.toFixed(1)}%`
            : '—',
        ],
        ['Employees', result.total_employees?.toLocaleString() ?? '—'],
        [
          'Taxonomy Aligned',
          result.taxonomy_aligned_revenue_pct != null
            ? `${result.taxonomy_aligned_revenue_pct.toFixed(1)}%`
            : '—',
        ],
        ['Activities', result.primary_activities.join(', ') || '—'],
      ]
    : []

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">Upload ESG Report</h1>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-300 hover:border-indigo-300 hover:bg-slate-50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-4 text-slate-400" size={40} />
        {isDragActive ? (
          <p className="text-indigo-600 font-medium">Drop the PDF here…</p>
        ) : (
          <>
            <p className="text-slate-600 font-medium">
              Drag &amp; drop a PDF, or click to select
            </p>
            <p className="text-sm text-slate-400 mt-1">
              Supports ESG / Sustainability / Annual Reports
            </p>
          </>
        )}
        {acceptedFiles[0] && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-slate-600">
            <FileText size={14} />
            {acceptedFiles[0].name}
          </div>
        )}
      </div>

      {mutation.isPending && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-slate-600">
              <div className="animate-spin w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full" />
              Extracting ESG data from PDF…
            </div>
          </CardContent>
        </Card>
      )}

      {mutation.isError && (
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle size={16} />
              {(mutation.error as Error).message}
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={18} className="text-green-500" />
              <span className="font-semibold">
                Extracted: {result.company_name} ({result.report_year})
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {fields.map(([k, v]) => (
                <div
                  key={k}
                  className="flex justify-between border rounded px-3 py-2"
                >
                  <span className="text-slate-500">{k}</span>
                  <Badge variant="secondary">{v}</Badge>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <Button onClick={() => navigate('/taxonomy')}>
                Run Taxonomy Score →
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate('/companies')}
              >
                View All Companies
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
