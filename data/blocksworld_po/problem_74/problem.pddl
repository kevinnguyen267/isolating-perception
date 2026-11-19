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
		(ontable orange)
		(on blue orange)
		(on yellow blue)
		(clear yellow)
		(ontable red)
		(on green red)
		(clear green)

		(ontable purple)
		(clear purple)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on green purple)
		(clear green)

		(ontable red)
		(clear red)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(clear yellow)
		(ontable blue)
		(clear blue)
	))
)