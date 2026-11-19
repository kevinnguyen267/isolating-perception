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
		(ontable red)
		(clear red)
		(ontable green)
		(clear green)
		(ontable orange)
		(on yellow orange)
		(clear yellow)

		(ontable purple)
		(on blue purple)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable yellow)
		(clear yellow)
		(ontable orange)
		(on purple orange)
		(clear purple)

		(ontable green)
		(on red green)
		(on blue red)
		(clear blue)
	))
)