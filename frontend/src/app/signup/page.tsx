'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { Logo } from '@/components/ui/Logo'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Mail } from 'lucide-react'

const signupSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type SignupFormData = z.infer<typeof signupSchema>

export default function SignupPage() {
  const [signupComplete, setSignupComplete] = useState(false)
  const [signupEmail, setSignupEmail] = useState('')
  const [serverError, setServerError] = useState<string | null>(null)
  const [resending, setResending] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
  })

  const onSubmit = async (data: SignupFormData) => {
    setServerError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        emailRedirectTo: `${window.location.origin}/api/auth/callback`,
      },
    })

    if (error) {
      setServerError(error.message)
      return
    }

    // Fire GA4 sign_up event. No-op when the user hasn't accepted cookies
    // (window.gtag is only defined after <AnalyticsProvider> loads the tag).
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'sign_up', { method: 'email' })
    }

    setSignupEmail(data.email)
    setSignupComplete(true)
  }

  const handleResend = async () => {
    setResending(true)
    setResendSuccess(false)
    const supabase = createClient()
    const { error } = await supabase.auth.resend({
      type: 'signup',
      email: signupEmail,
    })
    if (error) {
      setServerError(error.message)
    } else {
      setResendSuccess(true)
    }
    setResending(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="text-center mb-8 flex justify-center">
          <Logo size="lg" />
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl text-slate-900">
              {signupComplete ? 'Check your email' : 'Create your account'}
            </CardTitle>
            <CardDescription>
              {signupComplete
                ? 'One more step to activate your account.'
                : 'Start automating your client reports today.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {signupComplete ? (
              <div className="space-y-4">
                <div className="flex flex-col items-center gap-3 py-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
                    <Mail className="h-6 w-6 text-indigo-600" />
                  </div>
                  <p className="text-sm text-slate-700 text-center leading-relaxed">
                    We&apos;ve sent a confirmation link to{' '}
                    <strong className="text-slate-900">{signupEmail}</strong>.
                    Click the link in the email to activate your account.
                  </p>
                </div>

                {resendSuccess && (
                  <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-700">
                    Confirmation email resent! Check your inbox and spam folder.
                  </div>
                )}

                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-2">Didn&apos;t receive the email?</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleResend}
                    disabled={resending || resendSuccess}
                  >
                    {resending ? 'Sending...' : resendSuccess ? 'Email Sent' : 'Resend Confirmation Email'}
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {serverError && (
                  <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                    {serverError}
                  </div>
                )}

                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@agency.com"
                    autoComplete="email"
                    {...register('email')}
                    aria-invalid={!!errors.email}
                  />
                  {errors.email && (
                    <p className="text-xs text-rose-600">{errors.email.message}</p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Min. 8 characters"
                    autoComplete="new-password"
                    {...register('password')}
                    aria-invalid={!!errors.password}
                  />
                  {errors.password && (
                    <p className="text-xs text-rose-600">{errors.password.message}</p>
                  )}
                </div>

                <Button
                  type="submit"
                  className="w-full bg-indigo-700 hover:bg-indigo-800 text-white"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Creating account\u2026' : 'Create Account'}
                </Button>

                <p className="text-xs text-slate-400 text-center">
                  By signing up, you agree to our{' '}
                  <Link href="/terms" className="text-indigo-600 hover:underline">Terms of Service</Link>
                  {' '}and{' '}
                  <Link href="/privacy" className="text-indigo-600 hover:underline">Privacy Policy</Link>.
                </p>
              </form>
            )}

            <p className="mt-4 text-center text-sm text-slate-500">
              Already have an account?{' '}
              <Link href="/login" className="text-indigo-700 hover:underline font-medium">
                Log in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
