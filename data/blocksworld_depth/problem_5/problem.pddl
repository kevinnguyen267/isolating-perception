(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable green)
		(clear green)
		(ontable yellow)
		(on purple yellow)
		(clear purple)

		(ontable orange)
		(clear orange)
		(ontable red)
		(on blue red)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(clear purple)
		(ontable red)
		(on green red)
		(clear green)

		(ontable orange)
		(on blue orange)
		(clear blue)
		(ontable yellow)
		(clear yellow)
	))
)