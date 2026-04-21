'use client'

// Add Client dialog — react-hook-form + Zod, calls POST /api/clients
// Opened from the Clients list page

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { X } from 'lucide-react'
import { toast } from 'sonner'
import { clientsApi } from '@/lib/api'
import { Input } from '@/components/ui/input'
import BusinessContextField, { BUSINESS_CONTEXT_MAX } from '@/components/clients/BusinessContextField'
import type { Client } from '@/types'

const schema = z.object({
  name: z.string().min(1, 'Client name is required'),
  website_url: z.string().optional(),
  industry: z.string().optional(),
  primary_contact_email: z.string().email('Invalid email').optional().or(z.literal('')),
  goals_context: z.string().max(BUSINESS_CONTEXT_MAX).optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onClientAdded: (client: Client) => void
}

export default function AddClientDialog({ open, onOpenChange, onClientAdded }: Props) {
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { goals_context: '' },
  })

  // Watched so BusinessContextField stays a controlled input (react-hook-form
  // only registers raw refs; this field needs full value/onChange control for
  // the AI-assist diff flow and the character counter).
  const goalsContext = watch('goals_context') ?? ''

  const onSubmit = async (values: FormValues) => {
    setServerError(null)
    try {
      const payload = {
        ...values,
        primary_contact_email: values.primary_contact_email || undefined,
      }
      const client = await clientsApi.create(payload)
      reset()
      toast.success('Client created successfully')
      // Nudge toward richer context after save — doesn't block, just informs.
      if (!values.goals_context || values.goals_context.trim().length === 0) {
        toast.warning('Reports will use generic AI analysis. Add business context anytime for more strategic insights.')
      }
      onClientAdded(client)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setServerError(msg || 'Failed to create client. Please try again.')
      toast.error(msg || 'Failed to create client. Please try again.')
    }
  }

  const handleClose = () => {
    reset()
    setServerError(null)
    onOpenChange(false)
  }

  if (!open) return null

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) handleClose() }}
    >
      {/* Panel */}
      <div className="relative w-full max-w-md rounded-xl bg-white p-6 shadow-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2
            className="text-lg font-semibold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            Add Client
          </h2>
          <button
            onClick={handleClose}
            className="rounded-md p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Client name <span className="text-rose-500">*</span>
            </label>
            <Input
              {...register('name')}
              placeholder="Acme Corporation"
              aria-invalid={!!errors.name}
            />
            {errors.name && (
              <p className="mt-1 text-xs text-rose-600">{errors.name.message}</p>
            )}
          </div>

          {/* Website */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Website</label>
            <Input
              {...register('website_url')}
              placeholder="https://acme.com"
              type="url"
            />
          </div>

          {/* Industry */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Industry</label>
            <Input
              {...register('industry')}
              placeholder="e.g. E-commerce, SaaS, Healthcare"
            />
          </div>

          {/* Contact email */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contact email</label>
            <Input
              {...register('primary_contact_email')}
              type="email"
              placeholder="jane@acme.com"
              aria-invalid={!!errors.primary_contact_email}
            />
            {errors.primary_contact_email && (
              <p className="mt-1 text-xs text-rose-600">{errors.primary_contact_email.message}</p>
            )}
          </div>

          {/* Business context (shared component — quality dot, counter, AI assist, hints) */}
          <BusinessContextField
            value={goalsContext}
            onChange={(next) => setValue('goals_context', next, { shouldDirty: true })}
            rows={3}
          />

          {serverError && (
            <p className="text-sm text-rose-600">{serverError}</p>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-800 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Adding…' : 'Add Client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
