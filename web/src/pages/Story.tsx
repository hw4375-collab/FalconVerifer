import { loadBench, useAsync } from '../lib/data'
import { CounterModel } from '../story/CounterModel'
import { Grammar } from '../story/Grammar'
import { Hero } from '../story/Hero'
import { Close, Lesson, Org } from '../story/Lesson'
import { Loop } from '../story/Loop'
import { Outcome } from '../story/Outcome'
import { ArabicCapability, Architecture, UnderHood, UseCases, Value } from '../story/Pitch'
import { Problem } from '../story/Problem'

export function Story() {
  const { data } = useAsync(loadBench)
  const arm = data?.arms.find((a) => a.key === 'falcon3b_arabic')
  const scale = data?.arms.find((a) => a.key === 'falcon3b_arabic_scale')

  return (
    <main>
      <Hero />
      {arm ? <Problem arm={arm} /> : <div className="h-[80vh]" />}
      <Loop />
      {arm ? <Value arm={arm} /> : <div className="h-[60vh]" />}
      <ArabicCapability />
      <Grammar />
      <CounterModel />
      {arm ? <Outcome arm={arm} scale={scale} /> : <div className="h-[90vh]" />}
      <Architecture />
      <UseCases />
      <UnderHood />
      <Lesson />
      <Close />
      <Org />
    </main>
  )
}
